# tests/test_logger.py
#
# Este módulo contém testes automatizados para o sistema de logging do template.
#
# Objetivos principais destes testes:
# - Verificar o ciclo de vida do logger (inicialização, ativação de arquivo e encerramento)
# - Garantir que mensagens gravadas cedo (antes do arquivo existir) sejam persistidas depois
# - Evitar que um teste interfira em outro, pois o módulo logging do Python é global
# - Reduzir problemas comuns no Windows, como arquivos de log "presos" (bloqueados)
#
# Termos importantes usados neste arquivo:
# - Idempotência: uma função pode ser chamada várias vezes e o resultado final continua correto.
#   Exemplo: chamar enable_file_logging() 3 vezes não deve criar 3 handlers nem duplicar linhas no log.
# - Flakiness: quando um teste passa às vezes e falha outras vezes, sem você ter mudado o código.
#   Isso costuma ocorrer por timing, buffers, escrita em disco ou arquivos temporários ainda abertos.
#
# Estes testes foram escritos de forma explícita e defensiva para que iniciantes entendam:
# - o que está sendo testado
# - por que cada etapa existe
# - quais limitações reais o logger possui


from __future__ import annotations

# =============================================================================
# Imports - bibliotecas padrão e dependências do projeto
# =============================================================================

import logging  # Usado para acessar o sistema global de logging do Python
from logging.handlers import RotatingFileHandler  # Import explícito evita alerta de tipagem no VS Code/Pylance
from pathlib import Path  # Manipulação segura de caminhos (muito importante no Windows)
from uuid import uuid4  # Gera identificadores únicos para nomes de logger

import pytest  # Framework de testes utilizado no projeto

from nicegui_app_template.core.logger import (  # Importa a API pública do módulo de logger do projeto
    LogConfig,
    create_bootstrapper,
    get_logger,
)

# =============================================================================
# Helpers - funções auxiliares usadas pelos testes
# =============================================================================


def _unique_logger_name(prefix: str = "ng_template_test") -> str:
    """
    Gera um nome único de logger.

    Motivo:
    - O módulo logging guarda loggers em cache por nome (ele "reutiliza" loggers)
    - Se dois testes usarem o mesmo nome, um pode herdar configuração do outro
    - Nomes únicos reduzem muito o risco de interferência entre testes
    """
    return f"{prefix}.{uuid4().hex}"  # Usa UUID para evitar colisões mesmo em execuções repetidas


def _read_text(path: Path) -> str:
    """
    Lê o conteúdo de um arquivo de texto em UTF-8.

    Motivo:
    - Centralizar a leitura de arquivos de log
    - Evitar exceção caso o arquivo ainda não exista
    """
    if not path.exists():  # Se não existe, é melhor retornar vazio do que quebrar o teste
        return ""
    return path.read_text(encoding="utf-8")  # UTF-8 reduz inconsistências em ambientes Windows


def _count_handlers(
    logger: logging.Logger, handler_type: type[logging.Handler]
) -> int:
    """
    Conta quantos handlers de um determinado tipo estão associados ao logger.

    Motivo:
    - Verificar idempotência (chamar a função várias vezes não deve duplicar handlers)
    - Exemplo: enable_file_logging() não deve anexar 3 RotatingFileHandlers ao mesmo logger
    """
    return sum(1 for handler in logger.handlers if isinstance(handler, handler_type))


def _flush_all_handlers(logger: logging.Logger) -> None:
    """
    Força o flush de todos os handlers do logger.

    Motivo:
    - Em alguns casos, mensagens ficam em buffer antes de irem para o arquivo
    - Se o teste ler o arquivo "cedo demais", pode parecer que o log não foi gravado
    - Isso é uma causa comum de flakiness (teste falha aleatoriamente)
    """
    for handler in list(logger.handlers):  # Faz cópia para evitar problemas se a lista mudar durante a iteração
        try:
            handler.flush()  # Garante que o handler tente gravar tudo o que estiver pendente
        except Exception:
            # Em testes, não queremos que uma falha de flush derrube o suite.
            # O flush é uma tentativa de aumentar confiabilidade, não uma dependência rígida.
            pass


def _make_config(name: str, log_file: Path) -> LogConfig:
    """
    Cria uma configuração de logger adequada para testes.

    Motivo:
    - Centralizar valores padrão usados nos testes
    - Evitar repetição e manter todos os testes consistentes
    """
    return LogConfig(
        name=name,
        level=logging.INFO,  # INFO é suficiente para validar mensagens sem tornar o teste verboso
        console=False,  # Evita poluir a saída do pytest/VS Code Test Explorer
        buffer_capacity=200,  # Capacidade suficiente para testes sem consumir memória demais
        file_path=log_file,  # Arquivo de log isolado dentro de tmp_path
        rotate_max_bytes=1024,  # Pequeno para permitir testes de rotação sem criar arquivos enormes
        rotate_backup_count=2,  # Limita backups para manter o ambiente temporário limpo
    )


def _cleanup_logger_by_name(logger_name: str) -> None:
    """
    Remove handlers e reseta o estado básico de um logger pelo nome.

    Motivo:
    - O logging é global e mantém loggers em cache
    - Se um teste falhar antes do shutdown, handlers podem ficar "pendurados"
    - No Windows, handlers de arquivo pendurados podem bloquear a remoção do arquivo temporário
    - Esta função é uma "segunda linha de defesa" para garantir limpeza
    """
    logger = logging.getLogger(logger_name)  # Recupera o logger global pelo nome

    # Remove e fecha handlers para liberar recursos (principalmente arquivos).
    for handler in list(logger.handlers):
        try:
            logger.removeHandler(handler)  # Impede que o logger continue usando o handler
        except Exception:
            # Teardown deve ser resiliente para não mascarar a falha real do teste
            pass

        try:
            handler.close()  # Fecha o handler (fundamental para liberar arquivo no Windows)
        except Exception:
            # Se já estiver fechado, não é um problema
            pass

    # Reseta o estado básico do logger para evitar efeitos colaterais em suites maiores.
    logger.propagate = True  # Volta para o padrão seguro; o bootstrapper ajusta isso quando necessário
    logger.setLevel(logging.NOTSET)  # Remove nível fixo e volta ao comportamento padrão do logging


# =============================================================================
# Fixtures - preparação e limpeza automática para os testes
# =============================================================================


@pytest.fixture
def logger_bootstrapper_ctx(tmp_path: Path):
    """
    Fixture que prepara um ambiente isolado de logging para cada teste.

    Entrega:
    - bootstrapper: controla o ciclo de vida do logger
    - root_name: nome único do logger raiz
    - log_file: caminho do arquivo de log temporário
    - root_logger: instância do logger raiz (obtida via logging.getLogger)

    Por que usar fixture aqui:
    - Se um assert falhar no meio do teste, o código "depois do assert" não roda
    - Sem fixture, o shutdown() poderia não acontecer, deixando o arquivo aberto no Windows
    - Com fixture, garantimos cleanup no bloco finally, mesmo se o teste falhar
    """
    root_name = _unique_logger_name("nicegui_app_template")  # Nome único para isolar o logger deste teste
    log_file = tmp_path / "logs" / "app.log"  # Caminho isolado por teste (tmp_path é diferente a cada execução)
    config = _make_config(root_name, log_file)  # Configuração padrão de teste

    bootstrapper = create_bootstrapper(config)  # Cria o bootstrapper que gerencia handlers e flush do buffer
    root_logger = logging.getLogger(root_name)  # Obtém o logger raiz (ele pode ser configurado depois pelo bootstrapper)

    try:
        # Entregamos os objetos para o teste usar.
        yield bootstrapper, root_name, log_file, root_logger
    finally:
        # Mesmo que o teste falhe, o finally sempre roda.
        # Isso evita recursos abertos no Windows e reduz falhas intermitentes.
        try:
            bootstrapper.shutdown()  # Tenta encerrar handlers do jeito oficial do módulo
        except Exception:
            # Teardown não deve quebrar o suite; a limpeza manual abaixo cobre os casos problemáticos
            pass

        _cleanup_logger_by_name(root_name)  # Limpeza adicional por segurança (principalmente em caso de falhas no teste)


# =============================================================================
# Tests - casos de teste do sistema de logging
# =============================================================================


def test_child_logger_propagation_rules_are_correct(
    logger_bootstrapper_ctx,
) -> None:
    """
    Verifica as regras de propagação.

    Conceito:
    - Logger raiz: centraliza handlers (arquivo/buffer) e não propaga
    - Loggers filhos: propagam para o logger raiz para que tudo seja gravado no mesmo lugar
    """
    bootstrapper, root_name, _log_file, _root_logger = logger_bootstrapper_ctx

    root_logger = bootstrapper.bootstrap()  # Inicializa handlers (buffer) e nível no logger raiz
    child_logger = get_logger(f"{root_name}.ui.pages.home")  # Logger filho deve propagar para o raiz

    assert root_logger.propagate is False  # Evita que mensagens subam para loggers acima e causem duplicação
    assert child_logger.propagate is True  # Garante centralização das mensagens no logger raiz


def test_buffered_logs_are_flushed_to_file_after_enable(
    logger_bootstrapper_ctx,
) -> None:
    """
    Verifica que logs feitos antes de ativar o arquivo são preservados.

    Fluxo esperado:
    1) bootstrap cria um buffer em memória (MemoryHandler)
    2) logs entram no buffer
    3) enable_file_logging cria o arquivo e "despeja" o buffer no disco
    """
    bootstrapper, root_name, log_file, root_logger = logger_bootstrapper_ctx

    bootstrapper.bootstrap()  # Ativa buffer em memória no logger raiz
    child_logger = get_logger(f"{root_name}.core.some_module")  # Logger filho propaga para o raiz

    child_logger.info("early message before file logging")  # Deve entrar no buffer
    child_logger.info("second early message")  # Deve entrar no buffer

    assert not log_file.exists()  # O arquivo ainda não deve existir antes do enable

    bootstrapper.enable_file_logging(file_path=log_file)  # Cria handler de arquivo e faz flush do buffer

    _flush_all_handlers(root_logger)  # Ajuda a evitar flakiness (teste não lê o arquivo cedo demais)
    content = _read_text(log_file)

    assert "early message before file logging" in content
    assert "second early message" in content


def test_enable_file_logging_without_bootstrap_still_works(
    logger_bootstrapper_ctx,
) -> None:
    """
    Verifica que enable_file_logging funciona mesmo sem bootstrap explícito.

    O que este teste garante:
    - enable_file_logging deve preparar o logger por conta própria (se necessário)
    - depois disso, logs devem ser gravados no arquivo normalmente

    Observação importante para iniciantes:
    - logs emitidos antes do bootstrap/enable podem ser perdidos
    - isso acontece porque o logger ainda não tem handlers e o nível padrão descarta INFO
    """
    bootstrapper, root_name, log_file, root_logger = logger_bootstrapper_ctx

    bootstrapper.enable_file_logging(file_path=log_file)  # Deve inicializar o que for necessário internamente

    child_logger = get_logger(f"{root_name}.ui.pages.about")
    child_logger.info("message after implicit bootstrap")  # Agora deve ser gravado em arquivo

    _flush_all_handlers(root_logger)  # Reduz flakiness ao garantir persistência antes da leitura
    content = _read_text(log_file)

    assert "message after implicit bootstrap" in content


def test_enable_file_logging_is_idempotent(
    logger_bootstrapper_ctx,
) -> None:
    """
    Verifica idempotência de enable_file_logging.

    Idempotência, em termos simples:
    - você pode chamar a mesma função várias vezes
    - e o resultado final continua correto, sem efeitos colaterais indesejados

    Neste caso:
    - chamar enable_file_logging várias vezes não pode criar handlers duplicados
    - se criasse duplicados, o log teria linhas repetidas e ficaria difícil de diagnosticar
    """
    bootstrapper, _root_name, log_file, root_logger = logger_bootstrapper_ctx

    bootstrapper.bootstrap()  # Inicializa buffer e nível
    bootstrapper.enable_file_logging(file_path=log_file)  # Primeira chamada instala o handler
    bootstrapper.enable_file_logging(file_path=log_file)  # Segunda chamada não deve duplicar
    bootstrapper.enable_file_logging(file_path=log_file)  # Terceira chamada não deve duplicar

    assert _count_handlers(root_logger, RotatingFileHandler) == 1  # Deve existir apenas um handler de arquivo

    root_logger.info("one")
    root_logger.info("two")
    _flush_all_handlers(root_logger)  # Garante gravação antes de ler (menos flakiness)

    content = _read_text(log_file)
    assert "one" in content
    assert "two" in content


def test_shutdown_detaches_file_handler_to_avoid_windows_locks(
    logger_bootstrapper_ctx,
) -> None:
    """
    Verifica que shutdown remove e fecha o handler de arquivo.

    Por que isso é importante no Windows:
    - arquivos podem ficar bloqueados enquanto estiverem abertos
    - isso pode impedir limpeza de pastas temporárias e atrapalhar builds/updates
    """
    bootstrapper, _root_name, log_file, root_logger = logger_bootstrapper_ctx

    bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)

    assert _count_handlers(root_logger, RotatingFileHandler) == 1

    bootstrapper.shutdown()  # Encerramento explícito para validar efeito imediato

    assert _count_handlers(root_logger, RotatingFileHandler) == 0  # Handler deve ter sido removido


def test_file_rotation_creates_backup_when_size_exceeded(tmp_path: Path) -> None:
    """
    Verifica que a rotação de arquivo cria backups quando o tamanho é ultrapassado.

    Ideia:
    - configuramos um limite pequeno (rotate_max_bytes)
    - escrevemos várias mensagens grandes
    - esperamos que o RotatingFileHandler crie arquivos .1, .2, etc.
    """
    root_name = _unique_logger_name("nicegui_app_template")
    log_file = tmp_path / "logs" / "app.log"

    config = LogConfig(
        name=root_name,
        level=logging.INFO,
        console=False,
        buffer_capacity=10,
        file_path=log_file,
        rotate_max_bytes=600,  # Limite pequeno para forçar rotação rapidamente
        rotate_backup_count=2,  # Mantém poucos backups para não sujar tmp_path
    )

    bootstrapper = create_bootstrapper(config)
    root_logger = bootstrapper.bootstrap()
    bootstrapper.enable_file_logging(file_path=log_file)

    try:
        payload = "X" * 250  # Mensagem grande para ultrapassar o limite com poucas escritas
        for _ in range(10):
            root_logger.info("rotation-test %s", payload)

        _flush_all_handlers(root_logger)  # Evita flakiness garantindo que o disco já recebeu os dados

        assert log_file.exists()

        backup_1 = log_file.with_name(f"{log_file.name}.1")
        backup_2 = log_file.with_name(f"{log_file.name}.2")

        assert backup_1.exists() or backup_2.exists()
    finally:
        # try/finally aqui evita deixar o arquivo aberto caso um assert falhe.
        # Isso é importante no Windows para não bloquear a pasta temporária.
        try:
            bootstrapper.shutdown()
        finally:
            _cleanup_logger_by_name(root_name)


def test_logs_emitted_before_bootstrap_are_not_captured(
    logger_bootstrapper_ctx,
) -> None:
    """
    Verifica o comportamento real do logger antes do bootstrap.

    Observação importante para iniciantes:
    - antes do bootstrap, o logger raiz ainda não tem handlers configurados
    - além disso, o nível padrão efetivo costuma descartar mensagens INFO
    - por isso, mensagens emitidas muito cedo podem não aparecer no arquivo
    """
    bootstrapper, root_name, log_file, root_logger = logger_bootstrapper_ctx

    child_logger = get_logger(f"{root_name}.ui.pages.home")
    child_logger.info("early message that will be dropped")

    bootstrapper.enable_file_logging(file_path=log_file)

    _flush_all_handlers(root_logger)
    content = _read_text(log_file)

    assert "early message that will be dropped" not in content
