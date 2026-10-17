"""JSON command-line interface for any local automation tool; stdlib only."""
import argparse
import json
import sys
import time
from studio_client import StudioClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Loopback studio URL; defaults to OVS_URL/OVS_PORT or port 7865')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('status', 'start', 'voices'):
        commands.add_parser(name)
    job = commands.add_parser('job'); job.add_argument('job_id')
    history = commands.add_parser('history'); history.add_argument('--limit', type=int, default=10)
    folder = commands.add_parser('folder'); folder.add_argument('path')
    generate = commands.add_parser('generate')
    generate.add_argument('--text', required=True)
    generate.add_argument('--language', choices=('en', 'ta'), default='en')
    generate.add_argument('--voice', default='english_default')
    generate.add_argument('--feeling', default='neutral')
    generate.add_argument('--strength', type=float, default=0.7)
    generate.add_argument('--mode', choices=('classic', 'creative'), default='classic')
    generate.add_argument('--description', default='')
    generate.add_argument('--seed', type=int, default=42)
    generate.add_argument('--wait', action='store_true')
    convert = commands.add_parser('convert')
    convert.add_argument('input_path'); convert.add_argument('--target', required=True)
    convert.add_argument('--wait', action='store_true')
    reference = commands.add_parser('add-voice')
    reference.add_argument('input_path'); reference.add_argument('--name', required=True)
    args = parser.parse_args()
    client = StudioClient(args.url)
    if args.command == 'status': result = client.status()
    elif args.command == 'start': result = client.start()
    elif args.command == 'voices': result = client.voices()
    elif args.command == 'job': result = client.job(args.job_id)
    elif args.command == 'history': result = client.history(args.limit)
    elif args.command == 'folder': result = client.request('/api/storage', {'directory': args.path})
    elif args.command == 'add-voice': result = client.add_voice(args.name, args.input_path)
    elif args.command == 'convert': result = client.convert(args.input_path, args.target)
    else:
        result = client.generate(args.text, args.language, args.voice, args.feeling,
            args.strength, args.mode, args.description, args.seed)
    if getattr(args, 'wait', False):
        deadline = time.monotonic() + 1800
        while time.monotonic() < deadline:
            job = client.job(result['id'])
            if job['status'] in ('done', 'error'):
                result = job
                break
            time.sleep(2)
        else: raise TimeoutError('Still running after 30 minutes. Query job ' + result['id'] + ' later.')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('status') == 'error' else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
