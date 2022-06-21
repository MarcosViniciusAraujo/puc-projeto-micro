from .listenerguitarra import ListenerGuitarra, NotaGuitarra
from ..base import InterfaceBase
from ..nota_processada import NotaProcessada

from typing import Callable, List
from serial import Serial

__all__ = ['InterfaceGuitarra']


class InterfaceGuitarra(InterfaceBase):
    def __init__(self, serial_port: Serial, callback: Callable[[NotaProcessada], None], rangen: float):
        """Inicializa a interface da guitarra para o jogo

        Args:
            serial_port: porta Serial para ser utilizada
            callback: função para ser chamada ao receber uma nota valida
            rangen: range de consideração de uma nota (0 < range <= 0.5)
        """
        super().__init__()
        self._listener = ListenerGuitarra()
        self._porta = serial_port
        self._valores_dicionario: List[int] = list()
        self._callback_usuario = callback

        if isinstance(rangen, float) and 0 < rangen <= 0.5:
            self._range = rangen
        else:
            raise RuntimeError(f"Valor invalido para rangen: {rangen}")

    def atribui_notas(self, **kwargs):
        super().atribui_notas(**kwargs)
        for key in self._dicionario.keys():
            try:
                self._valores_dicionario.append(int(key))
            except ValueError:
                raise RuntimeError(f"Valor inválido: {key}")

    def _callback(self, nota: NotaGuitarra):
        """Faz o callback para o client

        Faz o processamento com o range
        """
        for valor in self._valores_dicionario:  # como sao poucas notas, não é necessário um bsearch
            if abs(nota.codigo - valor) <= self._range:
                self._callback_usuario(
                    NotaProcessada(
                        nome=self._dicionario[valor],
                        on=nota.on
                    )
                )

    def start(self):
        """Inicializa a captura das notas

        Retorna imediatamente
        """
        self._listener.callback = lambda x: self._callback(x)
        self._listener.input_port = self._porta
        self._listener.start()

    def stop(self):
        """Para a captura das notas"""
        self._listener.stop()
