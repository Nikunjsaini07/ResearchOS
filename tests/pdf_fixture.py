from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def sample_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 50 740 Td (Methods) Tj 0 -20 Td (We evaluated retrieval augmented generation using a fixed collection of documents.) Tj 0 -20 Td (Results) Tj 0 -20 Td (Retrieval improved factual consistency on the evaluated benchmark.) Tj 0 -20 Td (Limitations) Tj 0 -20 Td (The study only evaluated English language documents and short contexts.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


if __name__ == "__main__":
    from pathlib import Path

    Path("tests/fixture.pdf").write_bytes(sample_pdf())
