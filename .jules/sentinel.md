## 2024-05-15 - [Pydantic String Validation]
**Vulnerability:** Weak string validation in tool inputs. `start_date` and `end_date` lacked regex validation allowing arbitrary strings to be parsed and potentially forwarded to Google Earth Engine execution pipelines.
**Learning:** Adding validation via regex guarantees downstream integrations (like datetime parsing or API parameter injections) do not consume malformed string payloads.
**Prevention:** Use Pydantic's `pattern` constraint in `Field` declarations for all structurally defined string inputs (like dates, emails, or IDs) to prevent invalid data or injection vulnerabilities.

### Prompt Injection Prevention with Google GenAI
When using the `google-genai` SDK, untrusted user input directly interpolated into a large instruction string is a prompt injection vulnerability. Always separate system-level instructions from untrusted inputs by using the `system_instruction` parameter in `types.GenerateContentConfig` for the instructions, and placing only the user input/prompt into the standard `contents` parameter.
