import ast
import os

class StyleChecker:
    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'r', encoding='utf-8') as file:
            self.tree = ast.parse(file.read())
        self.lines = open(filepath, 'r', encoding='utf-8').readlines()
        self.report = []

    def generate_report(self):
        self.report.append(f"Total number of lines: {len(self.lines)}")
        self._check_structure()
        self._check_docstrings()
        self._check_type_annotations()
        self._check_naming_conventions()
        self._write_report()

    def _check_structure(self):
        packages, classes, functions = [], [], []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                packages += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                packages.append(node.module)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)

        self.report.append(f"Packages imported: {packages if packages else 'None'}")
        self.report.append(f"Classes defined: {classes if classes else 'None'}")
        self.report.append(f"Functions defined: {functions if functions else 'None'}")

    def _check_docstrings(self):
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                name = node.name
                if isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.ClassDef):
                    name = f"{node.parent.name}_{name}"
                if docstring:
                    self.report.append(f"{name} DocString: {docstring}\n")
                else:
                    self.report.append(f"{name} DocString not found.\n")

    def _check_type_annotations(self):
        missing_annotations = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    if arg.annotation is None:
                        missing_annotations.append(node.name)
                        break
                if node.returns is None:
                    missing_annotations.append(node.name)
        if missing_annotations:
            self.report.append(f"Functions missing type annotations: {missing_annotations}")
        else:
            self.report.append("All functions and methods have type annotations.")

    def _check_naming_conventions(self):
        incorrect_classes, incorrect_functions = [], []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and not node.name[0].isupper():
                incorrect_classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                if not all(x.islower() or x == '_' for x in node.name) and node.name != 'lower':
                    incorrect_functions.append(node.name)

        if incorrect_classes:
            self.report.append(f"Classes not using CamelCase: {incorrect_classes}")
        if incorrect_functions:
            self.report.append(f"Functions not using snake_case: {incorrect_functions}")
        if not incorrect_classes and not incorrect_functions:
            self.report.append("All names adhere to naming conventions.")

    def _write_report(self):
        report_path = f"style_report_{os.path.basename(self.filepath).replace('.py', '')}.txt"
        with open(report_path, 'w', encoding='utf-8') as report_file:
            report_file.write("\n".join(self.report))
        print(f"Report generated at: {report_path}")

def attach_parents(tree):
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

if __name__ == "__main__":
    filepath = input("Enter the path of the Python file to check: ")
    checker = StyleChecker(filepath)
    attach_parents(checker.tree)
    checker.generate_report()
