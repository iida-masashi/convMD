import os
from kikuchi_converter import convert_url

out_dir = "/Users/masashi/Documents/Obsidian Vault/資料/Web_Archives/kikuchi2"

failed_urls = [
    "http://www.kikuchi2.com/kounan/56-4.html",
    "http://www.kikuchi2.com/chusei/kgikei05.html",
    "http://www.kikuchi2.com/sheet/seisui44.html",
    "http://www.kikuchi2.com/sheet/heiketk10.html",
    "http://www.kikuchi2.com/heike/nagato/hnk16.html",
    "http://www.kikuchi2.com/taihei/tk19.html",
    "http://www.kikuchi2.com/encho/haiku5.html",
    "http://www.kikuchi2.com/sheet/seisui33.html"
]
# I omitted jinno.html because I already did it successfully via another script, 
# and qttk3504.html because the entire /taihei/qttk* directory is returning 404s according to the previous logs.

print(f"Retrying {len(failed_urls)} timed-out URLs...")
for url in failed_urls:
    convert_url(url, out_dir, follow_links=False)

print("Retry completed.")
