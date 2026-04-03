from typing import Dict, List, Any
from scripts.import_terms import get_domain_library_data
from app.schemas.domain import DOMAIN_LABELS


class DomainManager:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_domain_data(self, domain: str) -> Dict[str, Any]:
        if domain not in self._cache:
            self._cache[domain] = get_domain_library_data(domain)
        return self._cache[domain]

    def list_domains(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for domain, label in DOMAIN_LABELS.items():
            data = self.get_domain_data(domain)
            result.append(
                {
                    "id": domain,
                    "name": label,
                    "term_count": len(data.get("terms", {})),
                    "asr_mapping_count": len(data.get("asr_mapping", {})),
                }
            )
        return result

    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        data = self.get_domain_data(domain)
        categories = set()
        for _, info in data.get("terms", {}).items():
            if isinstance(info, dict):
                category = info.get("category")
                if category:
                    categories.add(category)

        return {
            "domain": domain,
            "term_count": len(data.get("terms", {})),
            "asr_mapping_count": len(data.get("asr_mapping", {})),
            "categories": sorted(categories),
        }


_default_manager: DomainManager | None = None


def get_domain_manager() -> DomainManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = DomainManager()
    return _default_manager
