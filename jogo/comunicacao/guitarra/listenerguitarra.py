from serial import Serial
from threading import Lock, Thread
from dataclasses import dataclass
from ..base import ListenerBase

from typing import Optional, List, Callable

__all__ = ['NotaGuitarra', 'ListenerGuitarra']


@dataclass
class NotaGuitarra:
    codigo: float
    on: bool


class ListenerGuitarra(ListenerBase):
    """Classe para ficar recebendo comandos da guitarra

    Possui duas propriedades e dois métodos principais:

        * input_port e callback
        * start() e stop()

    Possui uma propriedade especial:

        * range
    """
    def __init__(self):
        self._input_port: Optional[Serial] = None
        self._callbacks: List[Callable] = list()
        self._lock: Lock = Lock()
        self._range: float = 0.5
        # para a thread
        self._running: bool = False
        self._thread: Optional[Thread] = None
        # para o buffer
        self._nota_buffer: Optional[NotaGuitarra] = None

    @property
    def range(self):
        return self._range

    @range.setter
    def range(self, value):
        if isinstance(value, float):
            if value > 0.5:
                self._range = 0.5
            elif value < 0:
                self._range = 0
            else:
                self._range = value

    @property
    def input_port(self) -> Serial:
        return self._input_port

    @input_port.setter
    def input_port(self, port: Serial):
        """Configura a porta para receber os comandos do Serial.

        Levanta serial.SerialException caso a porta esteja inválida

        :param port: Porta Serial
        """

        if not port.is_open:
            port.open()     # levanta excecao caso a porta nao exista

        with self._lock:
            if self._input_port is not None:
                self._input_port.close()    # fecha a anterior
            self._input_port = port

        print(f"porta {port.name} configurada")
        return

    @property
    def callback(self):
        return self._callbacks

    @callback.setter
    def callback(self, func: Callable[[NotaGuitarra], None]):
        """Registra um callback para enviar a nota pressionada

        :param func: Função cujo parâmetro sera a `NotaGuitarra` pressionada
        """
        with self._lock:
            self._callbacks.append(func)

    def stop(self):
        """Para a captura da porta"""
        with self._lock:
            pass

    def _loop(self):
        """Faz o loop de escuta da porta"""
        while self._running and self._input_port.is_open:
            linha_bytes: bytes = self._input_port.readline()
            # decodificacao dos bytes
            try:
                linha: str = linha_bytes.decode()
            except UnicodeDecodeError:
                continue

            # decodificao do texto
            ret = NotaGuitarra(codigo=-1, on=False)
            linha_lista: List[str] = [x.strip() for x in linha.split(';')]
            if len(linha_lista) != 2:       # deve ter dois elementos
                continue
            identificador_raw: str = linha_lista[0]
            if not identificador_raw.isnumeric():   # deve ser numerico
                continue
            ret.codigo = float(identificador_raw)
            pressionado_raw: str = linha_lista[1]
            if pressionado_raw not in ('1', '0'):   # deve ser um binario
                continue
            ret.on = pressionado_raw.startswith('1')

            # processando de acordo com o buffer
            if self._nota_buffer is not None:
                # verificando se esta no range e inverteu o sinal
                if abs(self._nota_buffer.codigo - ret.codigo) < self._range and self._nota_buffer.on != ret.on:
                    # envia a nota afinal
                    with self._lock:
                        for c in self._callbacks:
                            c(ret)
            # atualiza o buffer
            self._nota_buffer = ret

    def start(self):
        """Inicia a captura da porta"""
        if not self._running and self._thread is None:
            self._running = True
            self._thread = Thread(target=self._loop)
            self._thread.start()
            print("Iniciando thread")

    def close(self):
        """Fecha a porta de captura"""
        if self._running:
            with self._lock:
                self._running = False
                self._thread.join()
                self._thread = None
