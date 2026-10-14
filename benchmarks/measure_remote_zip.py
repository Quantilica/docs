"""Soma o tamanho descompactado de ZIPs remotos lendo só o fim do arquivo (HTTP Range).

Uso: python -I measure_remote_zip.py urls.json saida.json [threads]

Uma requisição de sufixo por arquivo devolve o tamanho total (Content-Range) e o
diretório central; o restante nunca é baixado.
"""

import io
import json
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

TAIL = 256 * 1024


def fetch_tail(url, tries=4):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes=-{TAIL}"})
            with urllib.request.urlopen(req, timeout=180) as r:
                cr = r.headers["Content-Range"]  # bytes a-b/total
                total = int(cr.rsplit("/", 1)[1])
                return total, r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3 * (k + 1))
    raise last


class TailFile(io.RawIOBase):
    """Arquivo virtual: só o sufixo existe; ler fora dele é erro (não deve ocorrer)."""

    def __init__(self, total, tail):
        self.total, self.tail, self.pos = total, tail, 0
        self.base = total - len(tail)

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.total + off
        return self.pos

    def readinto(self, b):
        if self.pos < self.base:
            raise OSError(f"leitura fora do sufixo em {self.pos} (base {self.base})")
        chunk = self.tail[self.pos - self.base : self.pos - self.base + len(b)]
        b[: len(chunk)] = chunk
        self.pos += len(chunk)
        return len(chunk)


def inspect(url):
    total, tail = fetch_tail(url)
    with zipfile.ZipFile(TailFile(total, tail)) as z:
        infos = z.infolist()
        return {
            "url": url,
            "compressed_file": total,
            "entries": len(infos),
            "uncompressed": sum(i.file_size for i in infos),
            "names": [i.filename for i in infos][:3],
        }


if __name__ == "__main__":
    urls = [u for u, _ in json.load(open(sys.argv[1]))]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(inspect, urls))
    json.dump(res, open(sys.argv[2], "w"), indent=1)
    c = sum(r["compressed_file"] for r in res)
    u = sum(r["uncompressed"] for r in res)
    print(
        f"{len(res)} zips | compactado {c / 2**30:.2f} GiB | "
        f"descompactado {u / 2**30:.2f} GiB | razão {u / c:.1f}x"
    )
    for r in sorted(res, key=lambda r: -r["uncompressed"])[:5]:
        print(
            f"  {r['url'].rsplit('/', 1)[1]:22} {r['compressed_file'] / 2**20:9.1f} MiB -> "
            f"{r['uncompressed'] / 2**20:9.1f} MiB  ({r['names'][0]})"
        )
