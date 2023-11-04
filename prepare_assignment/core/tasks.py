from argparse import Namespace


def list_tasks(args: Namespace) -> None:
    print("list")


def remove_task(args: Namespace) -> None:
    print("remove")


def update_task(args: Namespace) -> None:
    print("update")


def remove_all_tasks(args: Namespace) -> None:
    print("remove all")
