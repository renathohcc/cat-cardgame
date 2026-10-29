"""Substituto minimo do jsonschema SO para o navegador (jsonschema depende de rpds-py, binario Rust sem
wheel WebAssembly). Os JSON ja sao validados pelos testes (pytest) antes do empacotamento."""


class ValidationError(Exception):
    message = ""
    absolute_path: tuple = ()


def validate(instance, schema, *args, **kwargs) -> None:
    return None
