"""Test-only NSS trust setup, using the image's existing libnss3 (no TLS bypass)."""

from __future__ import annotations

import ctypes
from pathlib import Path


def main() -> None:
    database = Path.home() / ".pki/nssdb"
    database.mkdir(parents=True, exist_ok=True)
    nss = ctypes.CDLL("libnss3.so")
    nss.NSS_InitReadWrite.argtypes = [ctypes.c_char_p]
    nss.NSS_InitReadWrite.restype = ctypes.c_int
    smime = ctypes.CDLL("libsmime3.so")
    smime.CERT_DecodeCertFromPackage.argtypes = [ctypes.c_char_p, ctypes.c_int]
    smime.CERT_DecodeCertFromPackage.restype = ctypes.c_void_p
    nss.PK11_GetInternalKeySlot.restype = ctypes.c_void_p
    nss.PK11_NeedUserInit.argtypes = [ctypes.c_void_p]
    nss.PK11_NeedUserInit.restype = ctypes.c_int
    nss.PK11_InitPin.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    nss.PK11_InitPin.restype = ctypes.c_int
    nss.PORT_GetError.restype = ctypes.c_int
    nss.PK11_ImportCert.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    nss.PK11_ImportCert.restype = ctypes.c_int
    nss.PK11_FreeSlot.argtypes = [ctypes.c_void_p]
    nss.CERT_GetDefaultCertDB.restype = ctypes.c_void_p
    nss.CERT_ChangeCertTrust.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    nss.CERT_ChangeCertTrust.restype = ctypes.c_int
    nss.CERT_DestroyCertificate.argtypes = [ctypes.c_void_p]
    nss.NSS_Shutdown.restype = ctypes.c_int
    if nss.NSS_InitReadWrite(f"sql:{database}".encode()) != 0:
        raise RuntimeError("NSS initialization failed")
    pem = Path("/fixtures/ca.crt").read_bytes()
    certificate = smime.CERT_DecodeCertFromPackage(pem, len(pem))
    if not certificate:
        raise RuntimeError("NSS certificate decode failed")
    # CERTCertTrust: sslFlags, emailFlags, objectSigningFlags. Valid/trusted CA.
    trust = (ctypes.c_uint * 3)(0x18, 0, 0)
    slot = nss.PK11_GetInternalKeySlot()
    if slot and nss.PK11_NeedUserInit(slot) and nss.PK11_InitPin(slot, None, None) != 0:
        raise RuntimeError(f"NSS token initialization failed: {nss.PORT_GetError()}")
    if not slot or nss.PK11_ImportCert(slot, certificate, 0, b"DWS synthetic CA", 0) != 0:
        raise RuntimeError("NSS CA import failed")
    if nss.CERT_ChangeCertTrust(nss.CERT_GetDefaultCertDB(), certificate, trust) != 0:
        raise RuntimeError(f"NSS CA trust failed: {nss.PORT_GetError()}")
    nss.PK11_FreeSlot(slot)
    nss.CERT_DestroyCertificate(certificate)
    if nss.NSS_Shutdown() != 0:
        raise RuntimeError("NSS shutdown failed")
    print("synthetic CA imported; certificate verification stays enabled")


if __name__ == "__main__":
    main()
