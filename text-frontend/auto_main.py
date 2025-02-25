"""Simple REPL frontend."""

import http
import random

import requests
import typer

app = typer.Typer()


# debug constants
USER = {"id": "1234", "display_name": "John Doe", "auth_method": "local"}


def _random_message_id():
    return str(random.randint(1000, 9999))


def _render_message(message: dict) -> str:
    """Render a message to the user."""
    if message["is_assistant"]:
        return f"Assistant: {message['text']}"
    return f"Prompter: {message['text']}"


@app.command()
def main(backend_url: str = "http://127.0.0.1:8080", api_key: str = "1234"):
    """automates tasks"""

    def _post(path: str, json: dict) -> dict:
        response = requests.post(f"{backend_url}{path}", json=json, headers={"X-API-Key": api_key})
        response.raise_for_status()
        if response.status_code == http.HTTPStatus.NO_CONTENT:
            return None
        return response.json()

    def gen_random_text():
        return " ".join([random.choice(["hello", "world", "foo", "bar"]) for _ in range(10)])

    def gen_random_ranking(messages):
        """rank messages randomly and return list of indexes in order of rank randomly"""
        print("Ranking")
        print(messages)
        print(len(messages))
        ranks = [i for i in range(len(messages))]
        shuffled = random.shuffle(ranks)
        print(ranks)
        print(shuffled)
        return ranks

    tasks = [_post("/api/v1/tasks/", {"type": "random", "user": USER})]
    q = 0
    while tasks:
        task = tasks.pop(0)
        print(task)

        match (task["type"]):
            case "initial_prompt":
                typer.echo("Please provide an initial prompt to the assistant.")
                if task["hint"]:
                    typer.echo(f"Hint: {task['hint']}")
                # acknowledge task
                message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})

                prompt = gen_random_text()
                user_message_id = _random_message_id()
                # send interaction
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "text_reply_to_message",
                        "message_id": message_id,
                        "task_id": task["id"],
                        "user_message_id": user_message_id,
                        "text": prompt,
                        "user": USER,
                    },
                )
                tasks.append(new_task)

            case "label_initial_prompt":
                typer.echo("Label the following prompt:")
                typer.echo(task["prompt"])
                # acknowledge task
                message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})

                valid_labels = task["valid_labels"]

                labels_dict = None
                if task["mode"] == "simple" and len(valid_labels) == 1:
                    answer = random.choice([True, False])
                    labels_dict = {valid_labels[0]: 1 if answer else 0}
                else:
                    while labels_dict is None:
                        labels = random.sample(valid_labels, random.randint(1, len(valid_labels)))
                        if all([label in valid_labels for label in labels]):
                            labels_dict = {
                                label: 1 if label != "lang_mismatch" and label in labels else 0
                                for label in valid_labels
                            }
                        else:
                            invalid_labels = [label for label in labels if label not in valid_labels]
                            typer.echo(f"Invalid labels: {', '.join(invalid_labels)}. Valid: {', '.join(valid_labels)}")

                # send labels
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "text_labels",
                        "message_id": task["message_id"],
                        "task_id": task["id"],
                        "text": task["prompt"],
                        "labels": labels_dict,
                        "user": USER,
                    },
                )
                tasks.append(new_task)
            case "prompter_reply":
                # acknowledge task
                message_id = _random_message_id()
                user_message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})
                # send interaction
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "text_reply_to_message",
                        "message_id": message_id,
                        "task_id": task["id"],
                        "user_message_id": user_message_id,
                        "text": gen_random_text(),
                        "user": USER,
                    },
                )
                tasks.append(new_task)

            case "assistant_reply":
                # acknowledge task
                message_id = _random_message_id()
                user_message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})
                # send interaction
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "text_reply_to_message",
                        "message_id": message_id,
                        "task_id": task["id"],
                        "user_message_id": user_message_id,
                        "text": gen_random_text(),
                        "user": USER,
                    },
                )
                tasks.append(new_task)

            case "rank_prompter_replies" | "rank_assistant_replies":
                # acknowledge task
                message_id = _random_message_id()
                user_message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})
                # send interaction
                ranking = gen_random_ranking(task["replies"])
                print(ranking)
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "message_ranking",
                        "message_id": message_id,
                        "task_id": task["id"],
                        "ranking": ranking,
                        "user": USER,
                    },
                )
                tasks.append(new_task)

            case "rank_initial_prompts":
                # acknowledge task
                message_id = _random_message_id()
                user_message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})
                # send interaction
                ranking = gen_random_ranking(task["prompots"])
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "message_ranking",
                        "message_id": message_id,
                        "ranking": ranking,
                        "user": USER,
                    },
                )
                tasks.append(new_task)

            case "label_prompter_reply" | "label_assistant_reply":
                # acknowledge task
                typer.echo("Here is the conversation so far:")
                for message in task["conversation"]["messages"]:
                    typer.echo(_render_message(message))

                typer.echo("Label the following reply:")
                typer.echo(task["reply"])
                message_id = _random_message_id()
                user_message_id = _random_message_id()
                _post(f"/api/v1/tasks/{task['id']}/ack", {"message_id": message_id})
                valid_labels = task["valid_labels"]

                labels_dict = None
                if task["mode"] == "simple" and len(valid_labels) == 1:
                    answer = random.choice([True, False])
                    labels_dict = {valid_labels[0]: 1 if answer else 0}
                else:
                    while labels_dict is None:
                        labels = random.sample(valid_labels, random.randint(1, len(valid_labels)))
                        if all([label in valid_labels for label in labels]):
                            labels_dict = {
                                label: 1 if label != "lang_mismatch" and label in labels else 0
                                for label in valid_labels
                            }
                        else:
                            invalid_labels = [label for label in labels if label not in valid_labels]
                            typer.echo(f"Invalid labels: {', '.join(invalid_labels)}. Valid: {', '.join(valid_labels)}")
                # send interaction
                new_task = _post(
                    "/api/v1/tasks/interaction",
                    {
                        "type": "text_labels",
                        "message_id": task["message_id"],
                        "task_id": task["id"],
                        "text": task["reply"],
                        "labels": labels_dict,
                        "user": USER,
                    },
                )
                tasks.append(new_task)
            case "task_done":
                typer.echo("Task done!")
                # rerun with new task slected from above cases
                # add a new task
                q += 1
                if q == 10:
                    typer.echo("Task done!")
                    break
                tasks = [_post("/api/v1/tasks/", {"type": "random", "user": USER})]
                #
            case _:
                typer.echo(f"Unknown task type {task['type']}")
                # rerun with new task slected from above cases


if __name__ == "__main__":
    app()
