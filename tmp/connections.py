import ast
import os

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.current_class = None
        self.current_method = None
        self.classes = {}
        self.calls = {}
        self.set_attributes = {}
        self.all_methods = set()
        self.methods_in_scope = set()

    def visit_ClassDef(self, node):
        self.current_class = node.name
        if self.current_class not in self.classes:
            self.classes[self.current_class] = {}
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        if self.current_class is not None:
            self.current_method = node.name
            if self.current_method not in self.classes[self.current_class]:
                self.classes[self.current_class][self.current_method] = {
                    'calls': set(),
                    'called_by': set(),
                    'attributes_set': set()
                }
            self.methods_in_scope.add(self.current_method)
            self.generic_visit(node)
            self.current_method = None

    def visit_Call(self, node):
        if self.current_method is not None:
            called_method = self.get_call_name(node)
            if called_method and called_method in self.methods_in_scope:
                self.classes[self.current_class][self.current_method]['calls'].add(called_method)
                if called_method in self.calls:
                    self.calls[called_method].add(self.current_method)
                else:
                    self.calls[called_method] = {self.current_method}
        self.check_qt_connections(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        if self.current_method is not None:
            for target in node.targets:
                if isinstance(target, ast.Attribute):
                    self.classes[self.current_class][self.current_method]['attributes_set'].add(target.attr)
        self.generic_visit(node)

    def get_call_name(self, node):
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def analyze_code(self, code):
        tree = ast.parse(code)
        self.visit(tree)
        for class_name, methods in self.classes.items():
            for method_name, method_info in methods.items():
                called_by_methods = self.calls.get(method_name, set())
                method_info['called_by'] = called_by_methods

    def extract_methods(self, code):
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.methods_in_scope.add(node.name)

    def check_qt_connections(self, node):
        """ Check for Qt signal connections like self.button.clicked.connect(self.method) """
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == 'connect':
                if len(node.args) == 1:
                    if isinstance(node.args[0], ast.Attribute):
                        connected_method = node.args[0].attr
                        if self.current_method is not None:
                            if connected_method not in self.classes[self.current_class]:
                                self.classes[self.current_class][connected_method] = {
                                    'calls': set(),
                                    'called_by': set(),
                                    'attributes_set': set()
                                }
                            self.classes[self.current_class][connected_method]['called_by'].add(self.current_method)
                            if connected_method in self.calls:
                                self.calls[connected_method].add(self.current_method)
                            else:
                                self.calls[connected_method] = {self.current_method}

def generate_html_table(classes):
    html = '<table border="1">'
    html += '<tr><th>Class</th><th>Method</th><th>Called By</th><th>Calls</th><th>Attributes Set</th></tr>'
    for class_name, methods in classes.items():
        for method_name, method_info in methods.items():
            called_by = ', '.join(f'<span style="color:magenta;">{m}</span>' if 'connect' in m else m for m in method_info['called_by'])
            calls = ', '.join(f'<span style="color:magenta;">{m}</span>' if 'connect' in m else m for m in method_info['calls'])
            attributes_set = ', '.join(method_info['attributes_set'])
            html += f'<tr><td>{class_name}</td><td>{method_name}</td><td>{called_by}</td><td>{calls}</td><td>{attributes_set}</td></tr>'
    html += '</table>'
    return html

def analyze_directory(directory, analyzer):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    code = f.read()
                    analyzer.extract_methods(code)
                    analyzer.analyze_code(code)

def main(python_file_path, src_directory):
    if not os.path.isfile(python_file_path):
        print(f"File not found: {python_file_path}")
        return

    if not os.path.isdir(src_directory):
        print(f"Directory not found: {src_directory}")
        return

    # Analyze the main file to extract method names
    main_analyzer = CodeAnalyzer()
    with open(python_file_path, 'r') as file:
        main_code = file.read()
        main_analyzer.extract_methods(main_code)
        main_analyzer.analyze_code(main_code)

    # Analyze the src directory
    src_analyzer = CodeAnalyzer()
    analyze_directory(src_directory, src_analyzer)

    # Merge the results
    merged_analyzer = CodeAnalyzer()
    merged_analyzer.classes = {**main_analyzer.classes, **src_analyzer.classes}
    merged_analyzer.calls = {**main_analyzer.calls, **src_analyzer.calls}
    merged_analyzer.set_attributes = {**main_analyzer.set_attributes, **src_analyzer.set_attributes}
    merged_analyzer.methods_in_scope = main_analyzer.methods_in_scope.union(src_analyzer.methods_in_scope)

    # Filter methods and calls to exclude those not defined in the main file or src directory
    filtered_classes = {}
    for class_name, methods in merged_analyzer.classes.items():
        filtered_methods = {}
        for method_name, method_info in methods.items():
            if method_name in merged_analyzer.methods_in_scope:
                filtered_methods[method_name] = {
                    'calls': {call for call in method_info['calls'] if call in merged_analyzer.methods_in_scope},
                    'called_by': {called_by for called_by in method_info['called_by'] if called_by in merged_analyzer.methods_in_scope},
                    'attributes_set': method_info['attributes_set']
                }
        if filtered_methods:
            filtered_classes[class_name] = filtered_methods

    html_table = generate_html_table(filtered_classes)

    with open('output.html', 'w') as output_file:
        output_file.write(html_table)

    print("HTML table generated and saved as output.html")

if __name__ == '__main__':
    main('main.py', 'src')
