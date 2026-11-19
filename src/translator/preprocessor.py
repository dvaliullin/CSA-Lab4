from __future__ import annotations

import re


class Preprocessor:
    _ADDRESS_PART_RE = re.compile(r"@([hHlL])\(\s*([^()]+?)\s*\)")

    def __init__(self) -> None:
        self.defines: dict[str, str] = {}
        self.macros: dict[str, tuple[list[str], list[str]]] = {}

    def _expand_address_parts(self, line: str) -> str:
        def replace(match: re.Match[str]) -> str:
            part, value_text = match.groups()
            try:
                value = int(value_text, 0)
            except ValueError as exc:
                raise ValueError(f"Address part operator requires a numeric value: {value_text}") from exc
            if part.lower() == "h":
                return str((value >> 16) & 0xFFFF)
            return str(value & 0xFFFF)

        return self._ADDRESS_PART_RE.sub(replace, line)

    def _substitute_defines(self, line: str) -> str:
        for dname, dval in self.defines.items():
            line = re.sub(rf"\b{re.escape(dname)}\b", dval, line)
        return self._expand_address_parts(line)

    def process(self, source_code: str) -> list[str]:
        lines = source_code.splitlines()
        result: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i].split("#")[0].split(";")[0].strip()
            if not line:
                i += 1
                continue

            # Константы: .equ NAME, VALUE или .set NAME, VALUE
            if line.startswith((".equ", ".set", "%define")):
                parts = line.split(maxsplit=2)
                if len(parts) >= 3:
                    name_part = parts[1].rstrip(",")
                    val_part = parts[2].lstrip(",").strip()
                    self.defines[name_part] = val_part
                i += 1
                continue

            # Условная компиляция: .ifdef NAME ... .endif
            if line.startswith((".ifdef", "%ifdef")):
                var = line.split()[1]
                has_var = var in self.defines
                i += 1
                block: list[str] = []
                while i < len(lines) and not lines[i].strip().startswith((".endif", "%endif")):
                    block.append(lines[i])
                    i += 1
                i += 1
                if has_var:
                    lines = lines[:i] + block + lines[i:]
                continue

            # Объявление макроса: .macro NAME arg1, arg2 ... .endm
            if line.startswith((".macro", "%macro")):
                parts = line.split(maxsplit=2)
                m_name = parts[1]
                param_str = parts[2] if len(parts) > 2 else ""
                param_names = [p.strip() for p in param_str.replace(",", " ").split() if p.strip()]

                m_body: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith((".endm", ".endmacro", "%endmacro")):
                    cleaned = lines[i].split("#")[0].split(";")[0].strip()
                    if cleaned:
                        m_body.append(cleaned)
                    i += 1
                i += 1
                self.macros[m_name] = (param_names, m_body)
                continue

            # Вызов макроса
            first_tok = line.split()[0]
            if first_tok in self.macros:
                param_names, m_body = self.macros[first_tok]
                args_str = line[len(first_tok) :].strip()
                args = [a.strip() for a in args_str.split(",") if a.strip()]

                for m_line in m_body:
                    expanded = m_line
                    for idx, p_name in enumerate(param_names):
                        val = args[idx] if idx < len(args) else ""
                        if not p_name.isdigit():
                            expanded = re.sub(rf"\\{re.escape(p_name)}\b", val, expanded)
                        expanded = expanded.replace(f"\\{idx + 1}", val)
                        expanded = expanded.replace(f"%{idx + 1}", val)
                    result.append(self._substitute_defines(expanded))
                i += 1
                continue

            # Подстановка констант
            result.append(self._substitute_defines(line))
            i += 1
        return result
