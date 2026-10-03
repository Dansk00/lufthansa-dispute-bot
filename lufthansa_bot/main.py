import os
import sys
import asyncio
import argparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lufthansa_bot.storage.db import DatabaseManager
from lufthansa_bot.engine.ai_generator import TextGenerator
from lufthansa_bot.engine.form_filler import LufthansaFeedbackAutomation
from lufthansa_bot.scheduler import DailyScheduler


def cmd_test_ai(args):
    print("=" * 60)
    print("GERADOR DE IA: TESTANDO CRIAÇÃO DE VARIAÇÃO EM INGLÊS")
    print("=" * 60)
    generator = TextGenerator()
    text = generator.generate()
    print(text)
    print("-" * 60)
    valid = generator.validate_facts(text)
    print(f"Validação de Fatos Obrigatórios: {'✅ VÁLIDO' if valid else '❌ FALTAM FATOS'}")


def cmd_run(args):
    print("=" * 60)
    print("EXECUTANDO SUBMISSÃO DO FORMULÁRIO LUFTHANSA")
    print("=" * 60)
    headless = args.headless
    automation = LufthansaFeedbackAutomation(headless=headless)
    result = asyncio.run(automation.run(mode="MANUAL_CLI"))
    print("\nResultado da Execução:")
    print(f"Status: {result['status']}")
    print(f"Protocolo / Ref: {result.get('protocol_number')}")
    print(f"Duração: {result.get('duration')}s")
    if result.get('screenshot'):
        print(f"Comprovante salvo em: {result['screenshot']}")
    if result.get('error'):
        print(f"Erro/Alerta: {result['error']}")


def cmd_portal(args):
    import uvicorn
    port = args.port
    print("=" * 60)
    print(f"INICIANDO PORTAL DE ACOMPANHAMENTO EM: http://127.0.0.1:{port}")
    print("=" * 60)
    from lufthansa_bot.web.app import app
    uvicorn.run(app, host="127.0.0.1", port=port)


def cmd_schedule(args):
    print("=" * 60)
    print("INICIANDO AGENDADOR DIÁRIO AUTOMÁTICO")
    print("=" * 60)
    scheduler = DailyScheduler(target_time=args.time)
    asyncio.run(scheduler.start())


def cmd_stats(args):
    db = DatabaseManager()
    stats = db.get_summary_stats()
    print("=" * 60)
    print("ESTATÍSTICAS DO LUFTHANSA CASE TRACKER")
    print("=" * 60)
    print(f"Total de execuções: {stats['total_runs']}")
    print(f"Sucessos: {stats['success_count']} ({stats['success_rate']}%)")
    print(f"Falhas/Bloqueios: {stats['fail_count']}")
    print(f"Último protocolo: {stats['last_success_protocol'] or 'Nenhum'}")
    print(f"Horário agendado: {stats['settings'].get('scheduled_time', '09:00')}")


def cmd_test_telegram(args):
    from datetime import datetime
    print("=" * 60)
    print("TESTE DE NOTIFICAÇÃO TELEGRAM")
    print("=" * 60)
    from lufthansa_bot.engine.telegram_notifier import TelegramNotifier
    notifier = TelegramNotifier()
    if not notifier.is_configured():
        print("⚠️ Telegram não configurado!")
        print("Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID como variáveis de ambiente.")
        return
    print("Enviando mensagem de teste para o seu Telegram...")
    ok = notifier.notify({
        "status": "TEST_SUCCESS",
        "protocol_number": "TEST-TELEGRAM-01",
        "duration": 1.2,
        "generated_text": "Mensagem de teste de notificação do Telegram para o Caso Lufthansa FB ID 42525052.",
        "screenshot": None,
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    print(f"Resultado do envio: {'✅ Entregue com sucesso!' if ok else '❌ Falha ao entregar.'}")


def main():
    parser = argparse.ArgumentParser(description="Lufthansa Feedback Bot & Case Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Comando a executar")

    # test-ai
    subparsers.add_parser("test-ai", help="Testa a geração de texto da IA e validação de fatos")

    # run
    p_run = subparsers.add_parser("run", help="Executa o robô de envio agora")
    p_run.add_argument("--headless", action="store_true", help="Executa o navegador em modo invisível")

    # portal
    p_portal = subparsers.add_parser("portal", help="Inicia o portal web local de acompanhamento")
    p_portal.add_argument("--port", type=int, default=8000, help="Porta HTTP (padrão: 8000)")

    # schedule
    p_sched = subparsers.add_parser("schedule", help="Inicia o agendador diário")
    p_sched.add_argument("--time", default="09:00", help="Horário diário no formato HH:MM (ex: 09:00)")

    # stats
    subparsers.add_parser("stats", help="Exibe estatísticas de envios registrados")

    # test-telegram
    subparsers.add_parser("test-telegram", help="Envia mensagem de teste para o Telegram")

    args = parser.parse_args()

    if args.command == "test-ai":
        cmd_test_ai(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "portal":
        cmd_portal(args)
    elif args.command == "schedule":
        cmd_schedule(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "test-telegram":
        cmd_test_telegram(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
