import json
import os
import sys
import argparse
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("pdfplumber is required. Install: pip install pdfplumber")
    sys.exit(1)


def extract_pdf(pdf_path):
    rows = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            meta = pdf.metadata or {}
            page_count = len(pdf.pages)
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                rows.append(
                    {
                        "file_name": pdf_path.name,
                        "path": str(pdf_path.resolve()),
                        "page": i,
                        "page_count": page_count,
                        "text": text,
                        "metadata": {k: v for k, v in meta.items() if v is not None},
                    }
                )
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
