"""Testing to generate mermaid code via templetes/template-functions."""


def task_code(taskname: str = "bim2sim task"):
    """Generate mermaid code representing a bim2sim task.

    WIP: so the some structure stuff like tpye of diagram is added here, later
    it should move to def generate_diagram".

    Args:
      taskname: name of the bim2sim taks of the plugin
      task_belongs: submodul the task belongs to of the bim2sim project

    Returns:
      Mermaid code of an task.
      WIP: check how to pipe. now it will printed
    """
    code_template = """
    flowchart TB
    subgraph "task {taskname}"
     tli["common.{taskname}"]
     subgraph reads & touches
      direction LR
      rli[/"None"/]
      toli[\"ifc_files"\]
     end
     extli("reads the IFC files of one or multiple domains inside bim2sim")
     end
    """
    code = code_template.format(taskname=taskname)
    print(code)


def generate_diagram():
    """Print mermaid code of the whole task structure of one bim2sim plugin."""
    pass


if __name__ == '__main__':
    task_code()
