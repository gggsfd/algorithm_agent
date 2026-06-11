import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DynamicKnowledgeStore:
    def __init__(self, base_path: str = "./data/dynamic_knowledge/current"):
        self.base_path = Path(base_path)
        self.materials_path = self.base_path / "materials"
        self.backups_path = self.base_path.parent / "backups"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.materials_path.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        return {
            "manifest": self._read_json("manifest.json", self._empty_manifest()),
            "terms": self._read_json("terms.json", {}),
            "asr_mapping": self._read_json("asr_mapping.json", {}),
            "asr_mapping_meta": self._read_json("asr_mapping_meta.json", {}),
            "candidate_terms": self._read_json("candidate_terms.json", {}),
            "candidate_asr_mapping": self._read_json("candidate_asr_mapping.json", {}),
            "candidate_asr_mapping_meta": self._read_json("candidate_asr_mapping_meta.json", {}),
            "course_profile": self._read_json("course_profile.json", {}),
        }

    def save_state(
        self,
        terms: dict[str, Any],
        asr_mapping: dict[str, str],
        asr_mapping_meta: dict[str, Any] | None = None,
        candidate_terms: dict[str, Any] | None = None,
        candidate_asr_mapping: dict[str, Any] | None = None,
        candidate_asr_mapping_meta: dict[str, Any] | None = None,
        course_profile: dict[str, Any] | None = None,
        materials: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        candidate_terms = candidate_terms or {}
        candidate_asr_mapping = candidate_asr_mapping or {}
        manifest = self._build_manifest(terms, asr_mapping, candidate_terms, candidate_asr_mapping, materials or [])
        self._atomic_write_json("terms.json", terms)
        self._atomic_write_json("asr_mapping.json", asr_mapping)
        self._atomic_write_json("asr_mapping_meta.json", asr_mapping_meta or {})
        self._atomic_write_json("candidate_terms.json", candidate_terms)
        self._atomic_write_json("candidate_asr_mapping.json", candidate_asr_mapping)
        self._atomic_write_json("candidate_asr_mapping_meta.json", candidate_asr_mapping_meta or {})
        self._atomic_write_json("course_profile.json", course_profile or {})
        self._atomic_write_json("manifest.json", manifest)
        return manifest

    def reset(self) -> dict[str, Any]:
        if self.base_path.exists() and any(self.base_path.iterdir()):
            self.backups_path.mkdir(parents=True, exist_ok=True)
            backup = self.backups_path / f"reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copytree(self.base_path, backup, dirs_exist_ok=True)
            for child in self.base_path.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        self.materials_path.mkdir(parents=True, exist_ok=True)
        return self.save_state({}, {}, {}, {}, {}, {}, {}, [])

    def save_material_file(self, source_path: str, material_id: str, filename: str) -> str:
        suffix = Path(filename).suffix
        safe_name = f"{material_id}{suffix}"
        target = self.materials_path / safe_name
        shutil.copy2(source_path, target)
        return str(target)

    def _read_json(self, filename: str, default: Any) -> Any:
        path = self.base_path / filename
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            broken = path.with_suffix(path.suffix + ".broken")
            os.replace(path, broken)
            return default

    def _atomic_write_json(self, filename: str, data: Any):
        self.base_path.mkdir(parents=True, exist_ok=True)
        tmp = self.base_path / f"{filename}.tmp"
        target = self.base_path / filename
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, target)

    def _build_manifest(
        self,
        terms: dict[str, Any],
        asr_mapping: dict[str, str],
        candidate_terms: dict[str, Any],
        candidate_asr_mapping: dict[str, Any],
        materials: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        existing = self._read_json("manifest.json", self._empty_manifest())
        return {
            "active_domain": "dynamic_current",
            "created_at": existing.get("created_at") or now,
            "updated_at": now,
            "material_count": len(materials),
            "term_count": len(terms),
            "asr_mapping_count": len(asr_mapping),
            "candidate_term_count": len(candidate_terms),
            "candidate_asr_mapping_count": len(candidate_asr_mapping),
            "materials": materials,
        }

    def _empty_manifest(self) -> dict[str, Any]:
        return {
            "active_domain": "dynamic_current",
            "created_at": "",
            "updated_at": "",
            "material_count": 0,
            "term_count": 0,
            "asr_mapping_count": 0,
            "candidate_term_count": 0,
            "candidate_asr_mapping_count": 0,
            "materials": [],
        }
