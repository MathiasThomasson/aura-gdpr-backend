import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

TEMPLATE_ROOT = Path(__file__).parent.parent / "templates" / "email"


def _render_template(template_name: str, context: Dict[str, str]) -> str:
    template_path = TEMPLATE_ROOT / template_name
    if not template_path.exists():
        return ""
    content = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        content = content.replace(f"{{{{ {key} }}}}", str(value))
    return content


async def send_email(to: str, subject: str, body: str) -> None:
    logger.info("EMAIL STUB to=%s subject=%s body=%s", to, subject, body)


async def send_templated_email(to: str, subject: str, template: str, context: Dict[str, str]) -> None:
    body = _render_template(template, context)
    await send_email(to, subject, body)
