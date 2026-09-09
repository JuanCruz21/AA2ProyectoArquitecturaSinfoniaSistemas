"""Pruebas de la capa de dominio.

Estas pruebas no necesitan base de datos ni servidor: comprueban las reglas de
negocio puras. Que se puedan escribir asi es precisamente la ventaja de tener
el dominio aislado de la infraestructura.
"""

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.entities import DomainError, Request, RequestStatus, User, UserRole


class TestMaquinaDeEstados:
    """Ciclo de vida de una solicitud de analisis."""

    def test_una_solicitud_nueva_empieza_pendiente(self):
        assert Request().status == RequestStatus.PENDING

    def test_transicion_valida_pendiente_a_en_analisis(self):
        solicitud = Request(status=RequestStatus.PENDING)
        solicitud.change_status(RequestStatus.IN_ANALYSIS)
        assert solicitud.status == RequestStatus.IN_ANALYSIS

    def test_flujo_completo_hasta_completada(self):
        solicitud = Request()
        solicitud.change_status(RequestStatus.IN_ANALYSIS)
        solicitud.change_status(RequestStatus.COMPLETED)
        assert solicitud.status == RequestStatus.COMPLETED

    def test_no_se_puede_completar_saltandose_el_analisis(self):
        solicitud = Request(status=RequestStatus.PENDING)
        with pytest.raises(DomainError, match="No se puede pasar"):
            solicitud.change_status(RequestStatus.COMPLETED)

    def test_una_solicitud_completada_es_un_estado_final(self):
        solicitud = Request(status=RequestStatus.COMPLETED)
        for destino in RequestStatus:
            with pytest.raises(DomainError):
                solicitud.change_status(destino)

    def test_una_solicitud_cancelada_es_un_estado_final(self):
        solicitud = Request(status=RequestStatus.CANCELLED)
        with pytest.raises(DomainError):
            solicitud.change_status(RequestStatus.IN_ANALYSIS)

    def test_se_puede_cancelar_mientras_no_este_cerrada(self):
        for origen in (RequestStatus.PENDING, RequestStatus.IN_ANALYSIS):
            solicitud = Request(status=origen)
            solicitud.change_status(RequestStatus.CANCELLED)
            assert solicitud.status == RequestStatus.CANCELLED

    def test_cambiar_de_estado_actualiza_la_fecha(self):
        solicitud = Request()
        anterior = solicitud.updated_at
        solicitud.change_status(RequestStatus.IN_ANALYSIS)
        assert solicitud.updated_at >= anterior


class TestAsignacionDeAnalista:
    """Regla de asignacion de responsable."""

    def test_se_puede_asignar_a_una_solicitud_pendiente(self):
        solicitud = Request()
        solicitud.assign_analyst(7)
        assert solicitud.assigned_analyst_id == 7

    def test_no_se_puede_asignar_a_una_solicitud_cerrada(self):
        solicitud = Request(status=RequestStatus.COMPLETED)
        with pytest.raises(DomainError, match="No se puede asignar"):
            solicitud.assign_analyst(7)


class TestRolesDeUsuario:
    """Comprobacion de roles en la entidad `User`."""

    def test_reconoce_su_propio_rol(self):
        usuario = User(role=UserRole.ANALYST)
        assert usuario.has_role(UserRole.ANALYST)
        assert usuario.has_role(UserRole.ADMIN, UserRole.ANALYST)

    def test_no_reconoce_un_rol_ajeno(self):
        assert not User(role=UserRole.CLIENT).has_role(UserRole.ADMIN)


class TestSeguridad:
    """Hash de contrasenas y tokens JWT."""

    def test_el_hash_no_guarda_la_contrasena_en_claro(self):
        hashed = hash_password("miClaveSecreta")
        assert hashed != "miClaveSecreta"
        assert verify_password("miClaveSecreta", hashed)

    def test_una_contrasena_incorrecta_no_valida(self):
        assert not verify_password("otraClave", hash_password("miClaveSecreta"))

    def test_dos_hashes_de_la_misma_clave_son_distintos(self):
        # Cada hash usa un `salt` aleatorio, por eso no deben coincidir.
        assert hash_password("misma") != hash_password("misma")

    def test_un_hash_corrupto_no_hace_fallar_la_verificacion(self):
        assert not verify_password("cualquiera", "esto-no-es-un-hash")

    def test_el_token_conserva_los_datos_del_usuario(self):
        token = create_access_token({"sub": "a@b.com", "user_id": 1, "role": "admin"})
        claims = decode_token(token)
        assert claims["sub"] == "a@b.com"
        assert claims["user_id"] == 1
        assert "exp" in claims

    def test_un_token_manipulado_se_rechaza(self):
        with pytest.raises(TokenError):
            decode_token("token.claramente.invalido")

    def test_un_token_caducado_se_rechaza(self):
        from datetime import timedelta

        caducado = create_access_token({"user_id": 1}, expires_delta=timedelta(seconds=-10))
        with pytest.raises(TokenError, match="expirado"):
            decode_token(caducado)
