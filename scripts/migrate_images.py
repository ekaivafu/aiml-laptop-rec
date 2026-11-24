import sqlite3
import re

def migrate():
    conn = sqlite3.connect("data/scraper.db")
    c = conn.cursor()
    
    # Check if image_url column exists in laptops
    cols = [col[1] for col in c.execute("PRAGMA table_info(laptops)").fetchall()]
    if "image_url" not in cols:
        print("Adding image_url column to laptops table...")
        c.execute("ALTER TABLE laptops ADD COLUMN image_url VARCHAR(500)")
        conn.commit()
    else:
        print("image_url column already exists in laptops table.")
        
    # Extract images from raw_products
    pattern1 = re.compile(r'<meta\s+property=[\"\']og:image[\"\']\s+content=[\"\']([^\"\']+)[\"\']', re.IGNORECASE)
    pattern2 = re.compile(r'<meta\s+content=[\"\']([^\"\']+)[\"\']\s+property=[\"\']og:image[\"\']', re.IGNORECASE)
    
    raw_rows = c.execute("SELECT laptop_id, raw_html FROM raw_products WHERE laptop_id IS NOT NULL AND raw_html IS NOT NULL").fetchall()
    
    id_to_img = {}
    for lid, html in raw_rows:
        if lid not in id_to_img:
            m = pattern1.search(html) or pattern2.search(html)
            if m:
                img_url = m.group(1).strip()
                if img_url.startswith("http"):
                    id_to_img[lid] = img_url
                    
    print(f"Extracted {len(id_to_img)} image URLs from raw_products.")
    
    # Update laptops table
    updated = 0
    for lid, img_url in id_to_img.items():
        c.execute("UPDATE laptops SET image_url = ? WHERE id = ?", (img_url, lid))
        updated += 1
        
    conn.commit()
    print(f"Updated {updated} laptop rows with image_url in scraper.db.")
    
    # Check total laptops and how many have image_url
    total = c.execute("SELECT count(*) FROM laptops").fetchone()[0]
    with_img = c.execute("SELECT count(*) FROM laptops WHERE image_url IS NOT NULL").fetchone()[0]
    print(f"Laptops summary: {with_img}/{total} have image_url.")
    
    conn.close()

if __name__ == "__main__":
    migrate()
