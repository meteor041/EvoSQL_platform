import pytest

from evosql_platform.config import BIRD_DIR
from evosql_platform.datasets.bird import BirdDatasetLoader


def test_bird_loader_has_sample_and_db_path() -> None:
    if not (BIRD_DIR / "dev.json").exists():
        pytest.skip("BIRD dev dataset is not available in this checkout.")
    loader = BirdDatasetLoader()
    sample = loader.get_sample(0)
    assert sample["db_id"]
    assert loader.get_db_path(sample["db_id"]).exists()
