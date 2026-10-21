// Python IntelliSense Autocomplete & Snippet Provider for CodeMirror
(function(mod) {
  if (typeof exports == "object" && typeof module == "object")
    mod(require("../../lib/codemirror"));
  else if (typeof define == "function" && define.amd)
    define(["../../lib/codemirror"], mod);
  else
    mod(CodeMirror);
})(function(CodeMirror) {
  "use strict";

  var Pos = CodeMirror.Pos;

  var PYTHON_KEYWORDS = [
    "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
    "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "True", "False", "None"
  ];

  var PYTHON_BUILTINS = [
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "classmethod", "compile", "complex", "delattr",
    "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter",
    "float", "format", "frozenset", "getattr", "globals", "hasattr",
    "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass",
    "iter", "len", "list", "locals", "map", "max", "memoryview", "min",
    "next", "object", "oct", "open", "ord", "pow", "print", "property",
    "range", "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type",
    "vars", "zip"
  ];

  var PYTHON_MODULES = [
    "math", "sys", "os", "json", "re", "collections", "itertools",
    "functools", "random", "datetime", "heapq", "bisect", "pandas",
    "matplotlib", "matplotlib.pyplot", "seaborn", "numpy"
  ];

  var MODULE_MEMBERS = {
    "math": [
      "sqrt", "factorial", "gcd", "lcm", "floor", "ceil", "trunc", "fabs",
      "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "degrees", "radians",
      "pi", "e", "tau", "inf", "nan", "log", "log10", "log2", "exp", "pow"
    ],
    "sys": [
      "stdin", "stdout", "stderr", "argv", "exit", "maxsize", "version"
    ],
    "stdin": [
      "read", "readline", "readlines"
    ],
    "stdout": [
      "write", "flush"
    ],
    "pd": [
      "read_csv", "DataFrame", "Series", "concat", "merge", "date_range"
    ],
    "pandas": [
      "read_csv", "DataFrame", "Series", "concat", "merge", "date_range"
    ],
    "plt": [
      "plot", "show", "figure", "title", "xlabel", "ylabel", "legend",
      "grid", "scatter", "bar", "hist", "boxplot", "savefig", "subplot", "subplots"
    ],
    "sns": [
      "lineplot", "scatterplot", "barplot", "histplot", "heatmap", "boxplot",
      "pairplot", "set_theme", "set_style", "load_dataset"
    ],
    "re": [
      "search", "match", "findall", "finditer", "sub", "split", "compile"
    ],
    "json": [
      "loads", "dumps", "load", "dump"
    ],
    "collections": [
      "Counter", "defaultdict", "deque", "namedtuple", "OrderedDict"
    ],
    "itertools": [
      "permutations", "combinations", "product", "accumulate", "chain", "groupby"
    ],
    "heapq": [
      "heappush", "heappop", "heapify", "nlargest", "nsmallest"
    ]
  };

  var PYTHON_SNIPPETS = [
    {
      trigger: "def",
      text: "def function_name(param1):\n    return param1",
      display: "def ... (fonction)",
      type: "snippet"
    },
    {
      trigger: "for",
      text: "for i in range(n):\n    ",
      display: "for i in range(...) (boucle indexée)",
      type: "snippet"
    },
    {
      trigger: "for_item",
      text: "for item in items:\n    ",
      display: "for item in items (itération)",
      type: "snippet"
    },
    {
      trigger: "if",
      text: "if condition:\n    \nelse:\n    ",
      display: "if ... else (conditionnel)",
      type: "snippet"
    },
    {
      trigger: "stdin_read",
      text: "import sys\nraw_data = sys.stdin.read().strip()\n",
      display: "sys.stdin.read() (lecture complète)",
      type: "snippet"
    },
    {
      trigger: "try",
      text: "try:\n    \nexcept Exception as e:\n    print(f'Erreur: {e}')",
      display: "try ... except Exception (gestion d'erreurs)",
      type: "snippet"
    },
    {
      trigger: "class",
      text: "class MyClass:\n    def __init__(self, name):\n        self.name = name\n",
      display: "class ... (classe POO)",
      type: "snippet"
    },
    {
      trigger: "plot",
      text: "import matplotlib.pyplot as plt\nplt.figure(figsize=(8, 5))\nplt.plot(x, y)\nplt.title('Titre du Graphique')\nplt.xlabel('Axe X')\nplt.ylabel('Axe Y')\nplt.grid(True)\nplt.show()",
      display: "plt.plot (tracé Matplotlib complet)",
      type: "snippet"
    }
  ];

  function pythonHint(cm, options) {
    var cur = cm.getCursor();
    var line = cm.getLine(cur.line);
    var end = cur.ch;
    var start = end;

    // Détection de mot ou membre d'objet (ex: sys.stdin ou math.sqrt)
    while (start && /[\w.]/.test(line.charAt(start - 1))) --start;
    var rawWord = line.slice(start, end);

    var list = [];
    var dotIdx = rawWord.lastIndexOf(".");

    if (dotIdx !== -1) {
      // Autocomplete sur propriété de module/objet (ex: math.sq -> membre 'sqrt')
      var objName = rawWord.slice(0, dotIdx);
      var propPrefix = rawWord.slice(dotIdx + 1).toLowerCase();
      var members = MODULE_MEMBERS[objName] || [];

      for (var i = 0; i < members.length; i++) {
        var m = members[i];
        if (m.toLowerCase().indexOf(propPrefix) === 0) {
          list.push({
            text: m,
            displayText: m + " (" + objName + ")",
            from: Pos(cur.line, start + dotIdx + 1),
            to: Pos(cur.line, end),
            render: function(elt, data, item) {
              elt.innerHTML = '<span class="hint-badge hint-badge-module">' + objName + '</span> <strong>' + item.text + '</strong>';
            }
          });
        }
      }
    } else {
      var word = rawWord.toLowerCase();

      // 1. Snippets
      for (var s = 0; s < PYTHON_SNIPPETS.length; s++) {
        var snip = PYTHON_SNIPPETS[s];
        if (!word || snip.trigger.toLowerCase().indexOf(word) === 0) {
          list.push({
            text: snip.text,
            displayText: snip.display,
            from: Pos(cur.line, start),
            to: Pos(cur.line, end),
            render: function(elt, data, item) {
              elt.innerHTML = '<span class="hint-badge hint-badge-snippet">SNIP</span> <span>' + item.displayText + '</span>';
            }
          });
        }
      }

      // 2. Mots-clés
      for (var k = 0; k < PYTHON_KEYWORDS.length; k++) {
        var kw = PYTHON_KEYWORDS[k];
        if (!word || kw.toLowerCase().indexOf(word) === 0) {
          list.push({
            text: kw,
            displayText: kw,
            from: Pos(cur.line, start),
            to: Pos(cur.line, end),
            render: function(elt, data, item) {
              elt.innerHTML = '<span class="hint-badge hint-badge-keyword">KEYWORD</span> <span>' + item.text + '</span>';
            }
          });
        }
      }

      // 3. Fonctions et builtins
      for (var b = 0; b < PYTHON_BUILTINS.length; b++) {
        var bi = PYTHON_BUILTINS[b];
        if (!word || bi.toLowerCase().indexOf(word) === 0) {
          list.push({
            text: bi,
            displayText: bi + "()",
            from: Pos(cur.line, start),
            to: Pos(cur.line, end),
            render: function(elt, data, item) {
              elt.innerHTML = '<span class="hint-badge hint-badge-builtin">BUILTIN</span> <strong>' + item.text + '</strong>()';
            }
          });
        }
      }

      // 4. Modules populaires
      for (var m = 0; m < PYTHON_MODULES.length; m++) {
        var modName = PYTHON_MODULES[m];
        if (!word || modName.toLowerCase().indexOf(word) === 0) {
          list.push({
            text: modName,
            displayText: modName,
            from: Pos(cur.line, start),
            to: Pos(cur.line, end),
            render: function(elt, data, item) {
              elt.innerHTML = '<span class="hint-badge hint-badge-module">MODULE</span> <span>' + item.text + '</span>';
            }
          });
        }
      }
    }

    return {
      list: list,
      from: Pos(cur.line, start),
      to: Pos(cur.line, end)
    };
  }

  CodeMirror.registerHelper("hint", "python", pythonHint);
  CodeMirror.hint = CodeMirror.hint || {};
  CodeMirror.hint.python = pythonHint;
});

