"""
Script de indexación de documentos ICFES → ChromaDB.

ESTRUCTURA DE CARPETAS:
    data/icfes_docs/
        general/           ← módulos comunes (Lectura Crítica, Razonamiento Cuantitativo, etc.)
            ejemplos/          PDFs con preguntas EXPLICADAS
            practica/          PDFs con preguntas de práctica
        programas/
            <slug-programa>/   ← módulo ESPECÍFICO de cada carrera
                ejemplos/
                practica/

SLUGS DE PROGRAMAS (sede Fusagasugá):
    administracion-de-empresas
    contaduria-publica
    licenciatura-ciencias-sociales
    ingenieria-electronica
    ingenieria-de-sistemas-y-computacion
    ingenieria-agronomica
    zootecnia
    licenciatura-educacion-fisica

USO:
    # Indexar toda la estructura (general + todos los programas)
    docker exec icfes_ai python -m app.scripts.indexar --raiz data/icfes_docs

    # Solo módulo general
    docker exec icfes_ai python -m app.scripts.indexar \\
        --directorio data/icfes_docs/general --modulo general

    # Módulo específico de un programa
    docker exec icfes_ai python -m app.scripts.indexar \\
        --directorio "data/icfes_docs/programas/ingenieria-de-sistemas-y-computacion" \\
        --modulo ingenieria-de-sistemas-y-computacion

    # Ver estadísticas
    docker exec icfes_ai python -m app.scripts.indexar --stats
"""

import os
import argparse
import hashlib
from pathlib import Path
from collections import Counter

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── Configuración ────────────────────────────────────────
CHROMA_HOST     = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT     = int(os.getenv("CHROMA_PORT", "8001"))
COLLECTION_NAME = "saberpro_docs"
CHUNK_SIZE      = 600
CHUNK_OVERLAP   = 120

# Subcarpetas de tipo dentro de cada módulo
SUBCARPETA_TIPO = {
    "ejemplos": "ejemplo",
    "practica": "practica",
}


# ── Utilidades ───────────────────────────────────────────

def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 60]


def _fix_encoding(text: str) -> str:
    """
    Corrige textos donde PyMuPDF interpreta bytes UTF-8 como CP1252.
    Ej.: 'Ã©' -> 'é', 'Ã³' -> 'ó', 'â€œ' -> '"'
    """
    try:
        fixed = text.encode("cp1252", errors="replace").decode("utf-8", errors="replace")
        def _ruido(t):
            return sum(1 for c in t if c in "Ã\x83\xc3\xc2\ufffd")
        return fixed if _ruido(fixed) < _ruido(text) else text
    except Exception:
        return text


def load_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(path))
            pages = [_fix_encoding(page.get_text()) for page in doc]
            doc.close()
            return "\n".join(pages)
        except ImportError:
            print("[Indexar] WARN: pymupdf no disponible.")
            return ""
        except Exception as e:
            print(f"[Indexar] WARN: {path.name}: {e}")
            return ""
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()


def get_chroma_collection(client):
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Indexación ───────────────────────────────────────────

def indexar_directorio(collection, model, dir_path: Path,
                       modulo: str, programa: str, fuente: str, tipo: str) -> int:
    """
    Indexa todos los PDFs/TXTs de dir_path.
    modulo: 'general' o slug del programa especifico.
    tipo:   'ejemplo' o 'practica'.
    """
    archivos = [f for f in sorted(dir_path.iterdir())
                if f.suffix.lower() in (".pdf", ".txt") and f.is_file()]
    if not archivos:
        print(f"[Indexar] INFO: Carpeta vacía: {dir_path}")
        return 0

    n_pdf = sum(1 for f in archivos if f.suffix.lower() == ".pdf")
    print(f"\n  [modulo={modulo} | tipo={tipo}] -> {len(archivos)} archivos ({n_pdf} PDF)")

    ids, docs, embeddings, metas = [], [], [], []
    for file_path in archivos:
        texto = load_file(file_path)
        if not texto.strip():
            print(f"    WARN: {file_path.name} vacío, se omite.")
            continue
        chunks = chunk_text(texto)
        print(f"    {file_path.name}: {len(chunks)} fragmentos")
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.md5(f"{modulo}_{tipo}_{file_path.name}_{i}".encode()).hexdigest()
            ids.append(doc_id)
            docs.append(chunk)
            embeddings.append(model.encode(chunk).tolist())
            metas.append({
                "modulo":   modulo,
                "tipo":     tipo,
                "fuente":   fuente,
                "archivo":  file_path.name,
                "programa": programa,
                "pagina":   str(i + 1),
            })

    if not ids:
        return 0

    for i in range(0, len(ids), 50):
        collection.upsert(
            ids=ids[i:i + 50],
            documents=docs[i:i + 50],
            embeddings=embeddings[i:i + 50],
            metadatas=metas[i:i + 50],
        )
    print(f"  OK {len(ids)} fragmentos insertados.")
    return len(ids)


def indexar_modulo(collection, model, modulo_path: Path, modulo: str, programa: str) -> int:
    """Indexa las subcarpetas ejemplos/ y practica/ de un directorio de módulo."""
    total = 0
    for subcarpeta, tipo in SUBCARPETA_TIPO.items():
        sub = modulo_path / subcarpeta
        if not sub.exists():
            print(f"[Indexar] INFO: {sub} no existe, se omite.")
            continue
        fuente = f"Cuadernillo {subcarpeta.capitalize()} ICFES [{modulo}]"
        total += indexar_directorio(collection, model, sub,
                                    modulo=modulo, programa=programa,
                                    fuente=fuente, tipo=tipo)
    return total


def mostrar_stats(collection):
    total = collection.count()
    print(f"\n{'='*64}")
    print(f"  COLECCION '{COLLECTION_NAME}'")
    print(f"{'='*64}")
    print(f"  Total fragmentos: {total}")
    if total == 0:
        print("  (sin documentos indexados aun)")
        print(f"{'='*64}\n")
        return

    result = collection.get(limit=min(total, 5000), include=["metadatas"])
    metas_list = result["metadatas"]

    por_modulo   = Counter(m.get("modulo",   "?") for m in metas_list)
    por_tipo     = Counter(m.get("tipo",     "?") for m in metas_list)
    por_archivo  = Counter(m.get("archivo",  "?") for m in metas_list)

    etiquetas_tipo = {
        "ejemplo":  "Ejemplos explicados",
        "practica": "Preguntas de practica",
        "pregunta": "Banco JSON",
    }

    print("\n  Por modulo:")
    for mod, n in sorted(por_modulo.items()):
        tag = " (comun a todos)" if mod == "general" else " (especifico)"
        print(f"    {mod}{tag}: {n} fragmentos")

    print("\n  Por tipo:")
    for tipo, n in sorted(por_tipo.items()):
        print(f"    {etiquetas_tipo.get(tipo, tipo)}: {n} fragmentos")

    print(f"\n  Archivos ({len(por_archivo)}):")
    for arch, n in sorted(por_archivo.items(), key=lambda x: -x[1])[:20]:
        print(f"    - {arch} ({n} frag.)")
    if len(por_archivo) > 20:
        print(f"    ... y {len(por_archivo) - 20} mas")
    print(f"{'='*64}\n")


# ── Main ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Indexar cuadernillos ICFES en ChromaDB")
    parser.add_argument("--raiz",       type=str,
                        help="Carpeta raiz (contiene general/ y programas/)")
    parser.add_argument("--directorio", type=str,
                        help="Directorio de modulo (contiene ejemplos/ y practica/)")
    parser.add_argument("--modulo",     type=str, default="general",
                        help="Slug del modulo: 'general' o nombre-del-programa")
    parser.add_argument("--programa",   type=str, default="General",
                        help="Etiqueta del programa para metadata. Default: General")
    parser.add_argument("--stats",      action="store_true",
                        help="Mostrar estadisticas y salir")
    args = parser.parse_args()

    print(f"[Indexar] Conectando a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}...")
    client = chromadb.HttpClient(
        host=CHROMA_HOST,
        port=CHROMA_PORT,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = get_chroma_collection(client)

    if args.stats:
        mostrar_stats(collection)
        return

    print("[Indexar] Cargando modelo all-MiniLM-L6-v2...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    total = 0

    if args.raiz:
        raiz = Path(args.raiz)

        # 1. Modulo general (comun a todos los programas)
        general_dir = raiz / "general"
        if general_dir.exists():
            print("\n[Indexar] Modulo GENERAL (Lectura Critica, Razonamiento Cuantitativo, etc.)")
            total += indexar_modulo(collection, model, general_dir,
                                    modulo="general", programa="General")
        else:
            print(f"[Indexar] INFO: {general_dir} no existe, se omite.")

        # 2. Modulos especificos por programa
        programas_dir = raiz / "programas"
        if programas_dir.exists():
            slugs = [d for d in sorted(programas_dir.iterdir()) if d.is_dir()]
            if slugs:
                print(f"\n[Indexar] Modulos ESPECIFICOS ({len(slugs)} programas)")
                for slug_dir in slugs:
                    slug = slug_dir.name
                    print(f"\n[Indexar] Programa: {slug}")
                    total += indexar_modulo(collection, model, slug_dir,
                                            modulo=slug, programa=slug)
            else:
                print("[Indexar] INFO: programas/ existe pero no tiene subcarpetas aun.")
        else:
            print(f"[Indexar] INFO: {programas_dir} no existe, se omiten modulos especificos.")

    elif args.directorio:
        total += indexar_modulo(collection, model, Path(args.directorio),
                                modulo=args.modulo, programa=args.programa)
    else:
        print("[Indexar] Debes usar --raiz, --directorio o --stats.")
        parser.print_help()
        return

    if total == 0:
        print("\nWARN: No se indexo nada. Verifica que las carpetas tengan PDFs o TXTs.")
    else:
        print(f"\nOK Indexacion completa. {total} fragmentos procesados.")
        mostrar_stats(collection)


if __name__ == "__main__":
    main()
