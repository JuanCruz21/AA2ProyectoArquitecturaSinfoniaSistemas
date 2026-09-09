"""Pruebas de integracion de la API.

Recorren la aplicacion completa (rutas, servicios, dominio y base de datos) para
comprobar el flujo de trabajo del laboratorio y las reglas de acceso por rol.
"""

from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD


class TestSistema:
    """Endpoints publicos de estado."""

    def test_health_check(self, client: TestClient):
        assert client.get("/health").json() == {"status": "healthy"}

    def test_la_raiz_indica_donde_esta_la_documentacion(self, client: TestClient):
        assert client.get("/").json()["docs"] == "/docs"


class TestAutenticacion:
    """Registro, inicio de sesion y proteccion de los endpoints."""

    def test_registro_e_inicio_de_sesion(self, client: TestClient):
        alta = client.post(
            "/api/auth/register",
            json={
                "email": "nuevo@test.com",
                "password": TEST_PASSWORD,
                "full_name": "Usuario Nuevo",
            },
        )
        assert alta.status_code == 201
        # El registro publico siempre crea un cliente, nunca un privilegiado.
        assert alta.json()["role"] == "client"
        # La respuesta jamas debe incluir la contrasena ni su hash.
        assert "password" not in alta.json() and "password_hash" not in alta.json()

        sesion = client.post(
            "/api/auth/login",
            json={"email": "nuevo@test.com", "password": TEST_PASSWORD},
        )
        assert sesion.status_code == 200
        assert sesion.json()["token_type"] == "bearer"

    def test_no_se_puede_registrar_el_mismo_email_dos_veces(self, client: TestClient):
        datos = {
            "email": "repetido@test.com",
            "password": TEST_PASSWORD,
            "full_name": "Primero",
        }
        assert client.post("/api/auth/register", json=datos).status_code == 201
        repetido = client.post("/api/auth/register", json=datos)
        assert repetido.status_code == 400
        assert "Ya existe" in repetido.json()["detail"]

    def test_se_rechaza_una_contrasena_demasiado_corta(self, client: TestClient):
        respuesta = client.post(
            "/api/auth/register",
            json={"email": "corta@test.com", "password": "123", "full_name": "Clave Corta"},
        )
        assert respuesta.status_code == 422  # Lo detiene la validacion de Pydantic

    def test_credenciales_incorrectas(self, client: TestClient, client_user):
        respuesta = client.post(
            "/api/auth/login",
            json={"email": "cliente@test.com", "password": "equivocada"},
        )
        assert respuesta.status_code == 401

    def test_sin_token_no_se_accede(self, client: TestClient):
        """Regresion: la cabecera Authorization debe leerse de verdad."""
        assert client.get("/api/auth/me").status_code == 401

    def test_con_token_valido_se_obtiene_el_perfil(self, client: TestClient, admin_headers):
        respuesta = client.get("/api/auth/me", headers=admin_headers)
        assert respuesta.status_code == 200
        assert respuesta.json()["email"] == "admin@test.com"

    def test_un_token_invalido_se_rechaza(self, client: TestClient):
        respuesta = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer no-es-un-token"}
        )
        assert respuesta.status_code == 401


class TestControlDeAcceso:
    """Reglas RBAC de los endpoints."""

    def test_solo_el_administrador_lista_usuarios(
        self, client: TestClient, admin_headers, client_headers
    ):
        assert client.get("/api/users/", headers=admin_headers).status_code == 200
        assert client.get("/api/users/", headers=client_headers).status_code == 403

    def test_un_cliente_no_puede_crear_fichas_de_cliente(
        self, client: TestClient, client_headers
    ):
        respuesta = client.post(
            "/api/clients/",
            headers=client_headers,
            json={"name": "Intruso", "email": "intruso@test.com"},
        )
        assert respuesta.status_code == 403

    def test_la_ruta_de_analistas_no_la_captura_el_parametro_dinamico(
        self, client: TestClient, admin_headers, analyst
    ):
        """Regresion: `/api/users/analysts` no debe interpretarse como un id."""
        respuesta = client.get("/api/users/analysts", headers=admin_headers)
        assert respuesta.status_code == 200
        assert [u["email"] for u in respuesta.json()] == ["analista@test.com"]

    def test_un_cliente_solo_ve_su_propio_perfil(
        self, client: TestClient, client_headers, client_user, analyst
    ):
        propio = client.get(f"/api/users/{client_user.id}", headers=client_headers)
        assert propio.status_code == 200

        ajeno = client.get(f"/api/users/{analyst.id}", headers=client_headers)
        assert ajeno.status_code == 403


class TestFlujoCompletoDelLaboratorio:
    """Recorrido de principio a fin: cliente, muestra, solicitud y resultado."""

    def test_flujo_completo(
        self,
        client: TestClient,
        receptionist_headers,
        analyst_headers,
        analyst,
        client_headers,
        client_user,
    ):
        # 1. Recepcion da de alta al cliente y lo enlaza con su cuenta.
        ficha = client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={
                "name": "Clinica Prueba",
                "email": "clinica@test.com",
                "phone": "600000000",
                "address": "Calle Falsa 123",
                "user_id": client_user.id,
            },
        )
        assert ficha.status_code == 201
        client_id = ficha.json()["id"]

        # 2. Recepcion registra la muestra (el codigo se genera solo).
        muestra = client.post(
            "/api/samples/",
            headers=receptionist_headers,
            json={"sample_type": "Sangre", "description": "Hemograma", "client_id": client_id},
        )
        assert muestra.status_code == 201
        assert muestra.json()["sample_code"].startswith("MUE-")
        sample_id = muestra.json()["id"]

        # 3. Recepcion crea la solicitud: nace en estado pendiente.
        solicitud = client.post(
            "/api/requests/",
            headers=receptionist_headers,
            json={"client_id": client_id, "sample_id": sample_id, "test_type": "Hemograma"},
        )
        assert solicitud.status_code == 201
        assert solicitud.json()["status"] == "pending"
        request_id = solicitud.json()["id"]

        # El evento REQUEST_CREATED debe haber generado la notificacion.
        avisos = client.get("/api/notifications/mine", headers=client_headers)
        assert avisos.status_code == 200
        assert len(avisos.json()) == 1
        assert "registrada" in avisos.json()[0]["message"]

        # 4. Recepcion asigna el analista.
        asignacion = client.put(
            f"/api/requests/{request_id}/analyst",
            headers=receptionist_headers,
            json={"analyst_id": analyst.id},
        )
        assert asignacion.status_code == 200
        assert asignacion.json()["assigned_analyst_id"] == analyst.id

        # 5. Aun no se puede registrar el resultado: falta pasar a analisis.
        prematuro = client.post(
            "/api/results/",
            headers=analyst_headers,
            json={"request_id": request_id, "result_value": "Normal"},
        )
        assert prematuro.status_code == 400
        assert "in_analysis" in prematuro.json()["detail"]

        # 6. El analista inicia el analisis.
        inicio = client.put(
            f"/api/requests/{request_id}/status",
            headers=analyst_headers,
            json={"status": "in_analysis"},
        )
        assert inicio.status_code == 200
        assert inicio.json()["status"] == "in_analysis"

        # 7. El analista registra el resultado y la solicitud se cierra sola.
        resultado = client.post(
            "/api/results/",
            headers=analyst_headers,
            json={
                "request_id": request_id,
                "result_value": "Hemoglobina 14.2 g/dL",
                "result_notes": "Valores dentro del rango normal",
            },
        )
        assert resultado.status_code == 201
        # El analista se toma del token, no del cuerpo de la peticion.
        assert resultado.json()["analyst_id"] == analyst.id

        final = client.get(f"/api/requests/{request_id}", headers=receptionist_headers)
        assert final.json()["status"] == "completed"

        # 8. El cliente consulta su resultado.
        consulta = client.get(f"/api/results/request/{request_id}", headers=client_headers)
        assert consulta.status_code == 200
        assert consulta.json()["result_value"] == "Hemoglobina 14.2 g/dL"

        # 9. Ha recibido avisos en cada hito del proceso.
        avisos_finales = client.get("/api/notifications/mine", headers=client_headers).json()
        assert len(avisos_finales) >= 3

        # 10. Puede marcar un aviso como leido.
        leida = client.put(
            f"/api/notifications/{avisos_finales[0]['id']}/read", headers=client_headers
        )
        assert leida.status_code == 200 and leida.json()["is_read"] is True


class TestReglasDeNegocioViaApi:
    """Comprobaciones de dominio a traves de los endpoints."""

    def _crear_solicitud(self, client, receptionist_headers, client_user_id=None):
        """Crea cliente, muestra y solicitud. Devuelve (client_id, request_id)."""
        ficha = client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={
                "name": "Cliente Regla",
                "email": "regla@test.com",
                "user_id": client_user_id,
            },
        ).json()
        muestra = client.post(
            "/api/samples/",
            headers=receptionist_headers,
            json={"sample_type": "Orina", "description": "", "client_id": ficha["id"]},
        ).json()
        solicitud = client.post(
            "/api/requests/",
            headers=receptionist_headers,
            json={
                "client_id": ficha["id"],
                "sample_id": muestra["id"],
                "test_type": "Uroanalisis",
            },
        ).json()
        return ficha["id"], solicitud["id"]

    def test_no_se_puede_solicitar_analisis_de_una_muestra_inexistente(
        self, client: TestClient, receptionist_headers
    ):
        ficha = client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={"name": "Cliente", "email": "c1@test.com"},
        ).json()
        respuesta = client.post(
            "/api/requests/",
            headers=receptionist_headers,
            json={"client_id": ficha["id"], "sample_id": 9999, "test_type": "Prueba"},
        )
        assert respuesta.status_code == 400
        assert "no encontrada" in respuesta.json()["detail"]

    def test_no_se_puede_analizar_la_muestra_de_otro_cliente(
        self, client: TestClient, receptionist_headers
    ):
        uno = client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={"name": "Cliente Uno", "email": "uno@test.com"},
        ).json()
        dos = client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={"name": "Cliente Dos", "email": "dos@test.com"},
        ).json()
        muestra = client.post(
            "/api/samples/",
            headers=receptionist_headers,
            json={"sample_type": "Sangre", "description": "", "client_id": uno["id"]},
        ).json()

        respuesta = client.post(
            "/api/requests/",
            headers=receptionist_headers,
            json={"client_id": dos["id"], "sample_id": muestra["id"], "test_type": "Prueba"},
        )
        assert respuesta.status_code == 400
        assert "otro cliente" in respuesta.json()["detail"]

    def test_solo_se_puede_asignar_a_un_analista_real(
        self, client: TestClient, receptionist_headers, admin_headers
    ):
        _, request_id = self._crear_solicitud(client, receptionist_headers)
        # Se intenta asignar el administrador, que no tiene rol de analista.
        admin_id = client.get("/api/auth/me", headers=admin_headers).json()["id"]
        respuesta = client.put(
            f"/api/requests/{request_id}/analyst",
            headers=receptionist_headers,
            json={"analyst_id": admin_id},
        )
        assert respuesta.status_code == 400
        assert "no es un analista" in respuesta.json()["detail"]

    def test_solo_el_analista_asignado_registra_el_resultado(
        self, client: TestClient, receptionist_headers, analyst, analyst_headers
    ):
        """La solicitud no esta asignada a este analista, asi que debe rechazarse."""
        _, request_id = self._crear_solicitud(client, receptionist_headers)
        client.put(
            f"/api/requests/{request_id}/status",
            headers=receptionist_headers,
            json={"status": "in_analysis"},
        )
        respuesta = client.post(
            "/api/results/",
            headers=analyst_headers,
            json={"request_id": request_id, "result_value": "Normal"},
        )
        assert respuesta.status_code == 400
        assert "analista asignado" in respuesta.json()["detail"]

    def test_no_se_puede_completar_cambiando_el_estado_a_mano(
        self, client: TestClient, receptionist_headers
    ):
        _, request_id = self._crear_solicitud(client, receptionist_headers)
        respuesta = client.put(
            f"/api/requests/{request_id}/status",
            headers=receptionist_headers,
            json={"status": "completed"},
        )
        assert respuesta.status_code == 400
        assert "POST /api/results/" in respuesta.json()["detail"]

    def test_una_transicion_invalida_devuelve_400(
        self, client: TestClient, receptionist_headers
    ):
        _, request_id = self._crear_solicitud(client, receptionist_headers)
        client.put(
            f"/api/requests/{request_id}/status",
            headers=receptionist_headers,
            json={"status": "cancelled"},
        )
        # Ya cancelada: no admite mas cambios.
        respuesta = client.put(
            f"/api/requests/{request_id}/status",
            headers=receptionist_headers,
            json={"status": "in_analysis"},
        )
        assert respuesta.status_code == 400
        assert "No se puede pasar" in respuesta.json()["detail"]


class TestAislamientoDeDatosDelCliente:
    """Un cliente nunca debe ver informacion de otros clientes."""

    def test_el_listado_de_clientes_solo_devuelve_la_ficha_propia(
        self, client: TestClient, receptionist_headers, client_headers, client_user
    ):
        client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={"name": "Mia", "email": "mia@test.com", "user_id": client_user.id},
        )
        client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={"name": "Ajena", "email": "ajena@test.com"},
        )

        visibles = client.get("/api/clients/", headers=client_headers).json()
        assert [c["name"] for c in visibles] == ["Mia"]

    def test_no_puede_consultar_la_ficha_de_otro_cliente(
        self, client: TestClient, receptionist_headers, client_headers
    ):
        ajena = client.post(
            "/api/clients/",
            headers=receptionist_headers,
            json={"name": "Ajena", "email": "ajena2@test.com"},
        ).json()
        respuesta = client.get(f"/api/clients/{ajena['id']}", headers=client_headers)
        assert respuesta.status_code == 403


class TestRutasPorEstado:
    """Regresion del orden de declaracion de las rutas."""

    def test_filtrar_por_estado_no_choca_con_el_id(
        self, client: TestClient, receptionist_headers
    ):
        """`/api/requests/status/pending` no debe leerse como `/{request_id}`."""
        respuesta = client.get("/api/requests/status/pending", headers=receptionist_headers)
        assert respuesta.status_code == 200
        assert isinstance(respuesta.json(), list)

    def test_un_estado_inexistente_se_rechaza(self, client: TestClient, receptionist_headers):
        respuesta = client.get("/api/requests/status/inventado", headers=receptionist_headers)
        assert respuesta.status_code == 422
