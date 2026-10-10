"""Збирає всі позиції фільтра воблерів з flagman.ua через внутрішній API."""

import json
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

CATALOG_URL = (
    "https://r.flagman.ua/site/catalog/168794/11250=6433;"
    "producer=4653,4649,4647,4641,4640,4635,4630,4598,4519,4507,4431,"
    "4404,4402,4401,4400,4399,4379,4354,4352,4287,4277,4265,4262,4261,"
    "4260,4252,4249,4248,4228,4207,4196,4193,4189,4170,4159"
)
GOODS_URL = "https://r.flagman.ua/api/goods/id/"
OUT_RAW = r"C:\Users\Gleam\OneDrive\Desktop\lures\flagman_raw.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "application/json",
}
BATCH = 32
WORKERS = 8


def get_json(url, tries=3):
    last = None
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            print(f"    retry {attempt}/{tries}: {exc}")
            time.sleep(2 * attempt)
    raise last


def main():
    print("1) Отримую перелік ID з каталогу...")
    catalog = get_json(CATALOG_URL)
    ids = catalog["data"]["goods"]
    ids = list(dict.fromkeys(str(i) for i in ids))
    print(f"   Знайдено позицій: {len(ids)}")

    batches = [ids[i : i + BATCH] for i in range(0, len(ids), BATCH)]
    print(f"2) Завантажую деталі: {len(batches)} батчів по {BATCH}, {WORKERS} потоків")

    items = {}
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(get_json, GOODS_URL + ",".join(b)): b for b in batches}
        for fut in as_completed(futures):
            batch = futures[fut]
            data = fut.result()
            for it in data.get("data", []):
                items[str(it["id"])] = it
            done += 1
            print(f"   [{done}/{len(batches)}] завантажено, всього товарів: {len(items)}")

    ordered = [items[i] for i in ids if i in items]
    with open(OUT_RAW, "w", encoding="utf-8") as fh:
        json.dump(ordered, fh, ensure_ascii=False)
    print(f"3) Готово. Збережено {len(ordered)} товарів -> {OUT_RAW}")

    # коротка діагностика полів
    if ordered:
        sample = ordered[0]
        print("   Приклад полів:", ", ".join(sorted(sample.keys())))
        print("   producer:", json.dumps(sample.get("producer"), ensure_ascii=False)[:200])
        print("   rating:", json.dumps(sample.get("rating"), ensure_ascii=False)[:200])
        print("   sell_status:", sample.get("sell_status"), "showPrice:", sample.get("showPrice"))


if __name__ == "__main__":
    main()
