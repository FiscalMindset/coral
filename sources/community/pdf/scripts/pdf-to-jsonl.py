import json
import sys
import argparse
from pathlib import Path

try:
    import fitz
except ImportError:
    print("PyMuPDF is required. Install: pip install pymupdf")
    sys.exit(1)


def extract_blocks(page):
    blocks = []
    raw = page.get_text("dict")["blocks"]
    for b in raw:
        if b["type"] == 0:
            for line in b["lines"]:
                for span in line["spans"]:
                    blocks.append(
                        {
                            "type": "text",
                            "text": span["text"],
                            "font": span["font"],
                            "size": round(span["size"], 1),
                            "bold": bool(span["flags"] & 2),
                            "italic": bool(span["flags"] & 1),
                            "color": span["color"],
                            "x0": round(span["bbox"][0], 1),
                            "y0": round(span["bbox"][1], 1),
                            "x1": round(span["bbox"][2], 1),
                            "y1": round(span["bbox"][3], 1),
                        }
                    )
        elif b["type"] == 1:
            blocks.append(
                {
                    "type": "image",
                    "width": b["width"],
                    "height": b["height"],
                    "x0": round(b["bbox"][0], 1),
                    "y0": round(b["bbox"][1], 1),
                    "x1": round(b["bbox"][2], 1),
                    "y1": round(b["bbox"][3], 1),
                }
            )
    return blocks


def extract_tables(page):
    tables = []
    for tab in page.find_tables().tables:
        rows = []
        for row in tab.extract():
            rows.append([cell.strip() if cell else "" for cell in row])
        tables.append(
            {
                "header": rows[0] if rows else [],
                "rows": rows[1:] if len(rows) > 1 else [],
                "bbox": {
                    "x0": round(tab.bbox[0], 1),
                    "y0": round(tab.bbox[1], 1),
                    "x1": round(tab.bbox[2], 1),
                    "y1": round(tab.bbox[3], 1),
                },
            }
        )
    return tables


def extract_images(page, pdf_path):
    images = []
    for img in page.get_images(full=True):
        xref = img[0]
        base = img[1]
        w, h = img[2], img[3]
        images.append(
            {
                "xref": xref,
                "width": w,
                "height": h,
                "bits": img[4] if len(img) > 4 else None,
            }
        )
    return images


def build_markdown(blocks):
    lines = []
    for b in blocks:
        if b["type"] == "text":
            text = b["text"].strip()
            if not text:
                continue
            if b["bold"] and b["size"] >= 14:
                lines.append(f"# {text}")
            elif b["bold"] and b["size"] >= 10:
                lines.append(f"## {text}")
            elif b["bold"] and b["size"] >= 9:
                lines.append(f"### {text}")
            elif b["bold"]:
                lines.append(f"**{text}**")
            elif b["italic"]:
                lines.append(f"*{text}*")
            else:
                lines.append(text)
    return "\n".join(lines)


def extract_pdf(pdf_path):
    rows = []
    try:
        doc = fitz.open(pdf_path)
        meta = doc.metadata or {}
        page_count = len(doc)
        for i in range(page_count):
            page = doc[i]
            blocks = extract_blocks(page)
            tables = extract_tables(page)
            images = extract_images(page, pdf_path)
            text = page.get_text("text") or ""
            markdown = build_markdown(blocks)
            rows.append(
                {
                    "file_name": pdf_path.name,
                    "path": str(pdf_path.resolve()),
                    "page": i + 1,
                    "page_count": page_count,
                    "text": text.strip(),
                    "markdown": markdown.strip(),
                    "blocks": blocks,
                    "tables": tables,
                    "images": images,
                    "metadata": {k: v for k, v in meta.items() if v},
                }
            )
        doc.close()
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}", file=sys.stderr)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Convert PDFs to JSONL for Coral")
    parser.add_argument("--dir", help="Directory of PDFs to process")
    parser.add_argument("--files", nargs="*", help="Individual PDF files to process")
    parser.add_argument(
        "--out",
        default=str(Path.home() / ".coral" / "pdf" / "pages.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--recursive", action="store_true", help="Scan --dir recursively"
    )
    args = parser.parse_args()

    pdf_paths = []
    if args.dir:
        d = Path(args.dir)
        pattern = "**/*.pdf" if args.recursive else "*.pdf"
        pdf_paths.extend(sorted(d.glob(pattern)))
    if args.files:
        pdf_paths.extend(Path(f) for f in args.files)

    if not pdf_paths:
        print("No PDF files found.", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    total_rows = 0
    with open(out_path, "w") as f:
        for pdf_path in pdf_paths:
            rows = extract_pdf(pdf_path)
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            total_rows += len(rows)
            print(f"  {pdf_path.name}: {len(rows)} page(s)")

    print(f"\nWrote {total_rows} row(s) to {out_path}")


if __name__ == "__main__":
    main()
