"""Contraseñas con scrypt y tokens de sesión. Nunca se guarda ni se registra un secreto en claro."""

import hashlib
import hmac
import secrets
from functools import lru_cache

# Parámetros de scrypt (N, r, p). Se guardan en el hash para poder subirlos más adelante.
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LONGITUD = 32
SCRYPT_MAXMEM = 64 * 1024 * 1024


def _derivar(contrasena: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        contrasena.encode("utf-8"), salt=sal, n=n, r=r, p=p, dklen=SCRYPT_LONGITUD, maxmem=SCRYPT_MAXMEM
    )


def hashear_clave(contrasena: str) -> str:
    """Devuelve `scrypt$N$r$p$sal$hash` con una sal aleatoria nueva."""
    sal = secrets.token_bytes(16)
    derivada = _derivar(contrasena, sal, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${sal.hex()}${derivada.hex()}"


def verificar_clave(contrasena: str, clave_hash: str) -> bool:
    """Compara en tiempo constante; un hash mal formado nunca es válido."""
    try:
        esquema, n, r, p, sal, esperado = clave_hash.split("$")
        if esquema != "scrypt":
            return False
        derivada = _derivar(contrasena, bytes.fromhex(sal), int(n), int(r), int(p))
        return hmac.compare_digest(derivada, bytes.fromhex(esperado))
    except (ValueError, TypeError):
        return False


@lru_cache
def hash_de_relleno() -> str:
    """Hash ficticio para gastar el mismo tiempo cuando el usuario no existe."""
    return hashear_clave(secrets.token_urlsafe(16))


def nuevo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 en hexadecimal: es lo único del token que llega a la base de datos."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
