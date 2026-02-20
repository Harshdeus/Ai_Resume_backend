from src.parse_resume import extract_resume
from langchain_ollama import OllamaLLM
from src.schema import json_structure
from prompt.structured_prompt import parse_resume_with_llm
from prompt.kpmg_prompt import wrap_kpmg_template_clean
from src.export_to_pdf import save_resume_as_pdf_styled

extract = extract_resume("Datasets/KPMG_Darshan_IT Procurement (Format).pdf")

print("==== EXTRACTED TEXT (DEBUG) ====")
print(extract)
print("================================")

llm = OllamaLLM(model="llama3.2:3b", temperature=0.0)

json_schema = json_structure()

structured = parse_resume_with_llm(extract, llm, json_schema)
print(structured)
# Example usage
formatted_resume = wrap_kpmg_template_clean(structured)
print(formatted_resume)
# save_resume_as_pdf_styled(formatted_resume)