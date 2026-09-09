"""Servicio de Muestras (capa de aplicacion)."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.domain.entities import DomainError, Sample
from app.domain.repositories import ClientRepository, SampleRepository


class SampleService:
    """Casos de uso relacionados con las muestras de laboratorio."""

    def __init__(
        self,
        sample_repository: SampleRepository,
        client_repository: ClientRepository,
    ) -> None:
        self.sample_repository = sample_repository
        self.client_repository = client_repository

    @staticmethod
    def generate_sample_code() -> str:
        """Genera un codigo de muestra unico con formato `MUE-AAAAMMDD-XXXXXX`."""
        fecha = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"MUE-{fecha}-{uuid4().hex[:6].upper()}"

    def create_sample(
        self,
        sample_type: str,
        description: str,
        client_id: int,
        sample_code: str | None = None,
    ) -> Sample:
        """Registra una muestra recibida (RF-05).

        Args:
            sample_code: Codigo manual. Si se omite se genera automaticamente,
                que es lo habitual para evitar colisiones.

        Raises:
            DomainError: Si el cliente no existe o el codigo ya esta en uso.
        """
        if not self.client_repository.get_by_id(client_id):
            raise DomainError(f"Cliente {client_id} no encontrado.")

        code = (sample_code or "").strip() or self.generate_sample_code()
        if self.sample_repository.get_by_code(code):
            raise DomainError(f"Ya existe una muestra con el codigo {code}.")

        return self.sample_repository.save(
            Sample(
                sample_code=code,
                sample_type=sample_type.strip(),
                description=description,
                client_id=client_id,
            )
        )

    def get_sample(self, sample_id: int) -> Sample | None:
        """Devuelve una muestra por su id."""
        return self.sample_repository.get_by_id(sample_id)

    def get_samples_by_client(self, client_id: int) -> list[Sample]:
        """Devuelve las muestras de un cliente."""
        return self.sample_repository.get_by_client(client_id)

    def get_all_samples(self) -> list[Sample]:
        """Devuelve todas las muestras."""
        return self.sample_repository.get_all()

    def update_sample(self, sample_id: int, **changes: Any) -> Sample:
        """Actualiza los datos de una muestra.

        Raises:
            DomainError: Si la muestra no existe.
        """
        sample = self.sample_repository.get_by_id(sample_id)
        if not sample:
            raise DomainError(f"Muestra {sample_id} no encontrada.")

        for key, value in changes.items():
            if value is not None and hasattr(sample, key):
                setattr(sample, key, value)
        return self.sample_repository.update(sample)
