# module imports
from threading import Lock, Timer

# local imports
import pygame

from .tela import Tela
from .constants import *
from .models.notas import NotaTela, NotaArquivo
from .comunicacao.notaprocessada import NotaProcessada


# typing imports
from typing import List, Optional
from .comunicacao.base import InterfaceBase


class Jogo:
    FPS = 30
    MILLIS = 1 / FPS * 1000

    def __init__(self,
                 instrumento: Optional[Instrumento],
                 musica_notas: str,
                 musica_som: str
                 ):
        """Inicia uma instância do jogo

        Args:
            instrumento (Instrumento): tipo do instrumento escolhido
            musica_notas (str): path das notas da música escolhida
            musica_som (str): path do audio da música escolhida
        """
        pygame.init()

        self.musica = musica_notas
        self.bpm = -1   # vai ser atribuido pelo self._carregar_notas
        pygame.mixer.music.load(musica_som)

        self.tipo_instrumento = instrumento
        self.interface: Optional[InterfaceBase] = None
        self.tela: Optional[Tela] = Tela()

        if instrumento == Instrumento.BATERIA:
            self._iniciar_bateria()
        elif instrumento == Instrumento.GUITARRA:
            self._iniciar_guitarra()

        # lista das notas da musica
        self.notas = self._carregar_notas(musica_notas)
        self.lock = Lock()  # para evitar concorrencia
        self.running = False
        self.musica_tocando = False

        # mapa de que notas estão sendo tocadas atualmente
        self.inputs = {k: False for k in ORDEM_CORDAS.keys()}

    def _iniciar_bateria(self):
        """Faz as configurações relativas a bateria"""
        import mido
        from .comunicacao.bateria.calibragembateria import calibrar_bateria
        from .comunicacao.bateria.interfacebateria import InterfaceBateria
        try:
            id_notas, porta = calibrar_bateria()
        except TypeError:
            print("Erro ao calibrar bateria (return None)")
            return

        # inicializacao da interface
        self.interface = InterfaceBateria(
            midi_port=mido.open_input(porta),  # noqa
            callback=lambda nota: self._callback_interface(nota)
        )

        self.interface.atribui_notas(
            nota1=id_notas[0],
            nota2=id_notas[1],
            nota3=id_notas[2],
            nota4=id_notas[3],
            nota5=id_notas[4],
        )
        self.interface.start()

    def _iniciar_guitarra(self):
        """Faz as configurações relativas a guitarra"""
        from serial import Serial
        from .comunicacao.guitarra.calibragemguitarra import calibrar_guitarra
        from .comunicacao.guitarra.interfaceguitarra import InterfaceGuitarra
        porta, range_considerado = calibrar_guitarra()

        # inicializacao da interface
        self.interface = InterfaceGuitarra(
            serial_port=Serial(porta),
            callback=lambda nota: self._callback_interface(nota),
            rangen=range_considerado
        )
        self.interface.atribui_notas(
            nota1=1.0,
            nota2=2.0,
            nota3=3.0,
            nota4=4.0,
            nota5=5.0
        )
        self.interface.start()

    def _carregar_notas(self, path_musica: str) -> List[NotaTela]:
        """Carrega as notas a partir do arquivo"""
        notas_carregadas: List[NotaArquivo] = list()
        try:
            with open(path_musica, 'r') as f:
                self.bpm = float(f.readline().strip())
                for linha in f:
                    linha_lista = linha.strip().split(',')
                    cor = linha_lista[0]                        # cor da nota
                    tempo = float(linha_lista[1]) / 1000        # tempo da nota
                    duracao = float(linha_lista[2]) if len(linha_lista) == 3 else 0     # duracao
                    notas_carregadas.append(NotaArquivo(cor, tempo, duracao))

        except Exception as e:
            print(e)
            print("Carregando notas mockadas")
            notas_carregadas: List[NotaArquivo] = [
                NotaArquivo('verde', 0.2564 + 3, 0),
                NotaArquivo('vermelho', 0.2564 * 2 + 3, 0),
                NotaArquivo('verde', 0.2564 * 3 + 3, 0),
                NotaArquivo('vermelho', 0.2564 * 4 + 3, 0),
                NotaArquivo('verde', 0.2564 * 5 + 3, 0),
                NotaArquivo('vermelho', 0.2564 * 6 + 3, 0),
            ]

        return [
            NotaTela.from_nota_arquivo(
                nota=nota,
                comprimento_acorde=self.tela.ALTURA_ACORDE,
                comprimento_divisao=self.tela.ALTURA_NOTA,
                bpm=self.bpm
            ) for nota in notas_carregadas
        ]

    def _callback_interface(self, nota: NotaProcessada):
        # pegando o id da nota pelo nome
        try:
            cor_nota_tocada: Cor = MAPA_NOME_NOTAS[nota.nome]
        except ValueError:
            print("Nota invalida (valor invalido): ", nota)
            return

        # salva nos inputs
        self.inputs[cor_nota_tocada] = nota.on

        # altera o valor na lista
        try:
            nova_lista = list()
            for nota_lista in self.notas:
                if (cor_nota_tocada == nota_lista.cor
                        and self.tela.LIMITE_ADIANTADO <= nota_lista.posicao <= self.tela.LIMITE_ATRASADO
                        and nota.on):
                    print("Acertou!")
                else:
                    nova_lista.append(nota_lista)
            self.notas = nova_lista

        except IndexError:
            print("Nota invalida (indice invalido): ", nota)

    def _feedback_interface(self):
        pass

    def checa_eventos(self):
        """Checa os eventos do pygame"""
        if not pygame.mixer.music.get_busy() and self.musica_tocando:
            self.running = False
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # temporario: funcionamento pelo teclado
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    self._callback_interface(NotaProcessada('nota1', event.type == pygame.KEYDOWN))
                if event.key == pygame.K_s:
                    self._callback_interface(NotaProcessada('nota2', event.type == pygame.KEYDOWN))
                if event.key == pygame.K_d:
                    self._callback_interface(NotaProcessada('nota3', event.type == pygame.KEYDOWN))
                if event.key == pygame.K_f:
                    self._callback_interface(NotaProcessada('nota4', event.type == pygame.KEYDOWN))
                if event.key == pygame.K_g:
                    self._callback_interface(NotaProcessada('nota5', event.type == pygame.KEYDOWN))

    def update(self):
        self.tela.desenha(self.inputs)

        # movendo as notas
        nova_lista: List[NotaTela] = list()

        with self.lock:
            for nota in self.notas:
                nota.posicao += self.MILLIS / 1000 * self.tela.ALTURA_NOTA * self.bpm / 60

                if nota.posicao > self.tela.LIMITE_ATRASADO:
                    print('Errou: ', nota)
                else:
                    self.tela.desenha_nota(nota.cor, nota.posicao)
                    nova_lista.append(nota)

        pygame.display.flip()
        self.notas = nova_lista

    def loop(self):
        clock = pygame.time.Clock()
        self.running = True
        # pygame.mixer.music.play()

        while self.running:
            clock.tick(self.FPS)
            self.checa_eventos()
            self.update()