import shopping
from config import Settings


def test_shopping_list(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert shopping.run_tool({"action": "read"}, s) == "The shopping list is empty."
    assert shopping.add(s, ["Milk", " eggs ", "milk"]) == "Added Milk, eggs. 2 items on the list."
    assert shopping.path(s) == tmp_path / "Shopping" / "list.md"
    assert shopping.run_tool({"action": "read"}, s) == "• Milk\n• eggs"
    assert shopping.remove(s, ["egg"]) == "Ticked off eggs. 1 left."
    assert shopping.clear(s) == "The shopping list is empty."
