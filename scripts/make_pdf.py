from fpdf import FPDF
from fpdf.enums import XPos, YPos

COMPANY = "MMNova Tech"


def build_pdf(path: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(0, 15, f"{COMPANY} - Company Profile", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 12)
    intro = (
        f"{COMPANY} is a software company delivering web, mobile, and "
        "AI-automation solutions for growing businesses. We turn operational "
        "bottlenecks into scalable, automated systems."
    )
    pdf.multi_cell(0, 7, intro, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Our Services", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 12)
    for line in (
        "- Web Development: sites, portals, and e-commerce.",
        "- Mobile Development: iOS and Android apps.",
        "- AI / Automation: workflow automation and LLM integrations.",
        "- Consulting: architecture and technical strategy.",
    ):
        pdf.multi_cell(0, 7, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Contact", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 7, "Email: akashbakshi.ai@gmail.com", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(path)


if __name__ == "__main__":
    build_pdf("app/assets/Company_Profile.pdf")
    print("Wrote app/assets/Company_Profile.pdf")
