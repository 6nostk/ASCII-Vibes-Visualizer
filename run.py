"""Punto de entrada: python run.py [--demo] [--fullscreen]"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser(description="ASCII-Vibes-Visualizer")
    ap.add_argument("--demo", action="store_true", help="usa una señal de audio sintética (sin captura real)")
    ap.add_argument("--fullscreen", action="store_true", help="arranca en pantalla completa")
    args = ap.parse_args()
    from asciiviz.app import App
    App(demo=args.demo, fullscreen=args.fullscreen).run()


if __name__ == "__main__":
    sys.exit(main())
