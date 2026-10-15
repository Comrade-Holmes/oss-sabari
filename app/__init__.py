"""
AllerGraph Application Package
Includes compatibility layer for Starlette Jinja2Templates to support both:
- Legacy signature: TemplateResponse(name, context, ...)
- Modern signature: TemplateResponse(request, name, context, ...)
"""

import starlette.templating

_orig_template_response = starlette.templating.Jinja2Templates.TemplateResponse

def _compat_template_response(self, *args, **kwargs):
    if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], dict):
        name = args[0]
        context = args[1]
        req = context.get("request")
        remaining_args = args[2:]
        return _orig_template_response(self, req, name, context, *remaining_args, **kwargs)
    elif len(args) == 1 and isinstance(args[0], str):
        name = args[0]
        context = kwargs.pop("context", {})
        req = kwargs.pop("request", None) or context.get("request")
        return _orig_template_response(self, req, name, context, **kwargs)
    return _orig_template_response(self, *args, **kwargs)

starlette.templating.Jinja2Templates.TemplateResponse = _compat_template_response
