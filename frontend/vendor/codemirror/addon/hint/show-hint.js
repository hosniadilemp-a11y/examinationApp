// CodeMirror show-hint addon for autocomplete
(function(mod) {
  if (typeof exports == "object" && typeof module == "object")
    mod(require("../../lib/codemirror"));
  else if (typeof define == "function" && define.amd)
    define(["../../lib/codemirror"], mod);
  else
    mod(CodeMirror);
})(function(CodeMirror) {
  "use strict";

  var HINT_ELEMENT_CLASS        = "CodeMirror-hint";
  var ACTIVE_HINT_ELEMENT_CLASS = "CodeMirror-hint-active";

  CodeMirror.showHint = function(cm, getHints, options) {
    if (!getHints) return cm.showHint(options);
    options = options || {};

    if (cm.state.completionActive) cm.state.completionActive.close();

    var completion = new Completion(cm, getHints, options);
    CodeMirror.signal(cm, "startCompletion", cm);
    if (completion.widget) return true;
  };

  function Completion(cm, getHints, options) {
    this.cm = cm;
    this.getHints = getHints;
    this.options = options;
    this.widget = null;
    this.debounce = 0;
    this.tick = 0;
    this.startPos = this.cm.getCursor("start");
    this.startLen = this.cm.getLine(this.startPos.line).length;

    var self = this;
    cm.on("cursorActivity", this.activityFunc = function() { self.cursorActivity(); });
    cm.on("blur", this.blurFunc = function() {
      setTimeout(function() {
        if (self.active()) {
          var activeEl = document.activeElement;
          if (!activeEl || !self.widget || !self.widget.hints || !self.widget.hints.contains(activeEl)) {
            self.close();
          }
        }
      }, 100);
    });
    this.update();
  }

  Completion.prototype = {
    close: function() {
      if (!this.active()) return;
      this.cm.state.completionActive = null;
      this.tick = null;
      this.cm.off("cursorActivity", this.activityFunc);
      if (this.blurFunc) this.cm.off("blur", this.blurFunc);

      if (this.widget) this.widget.close();
      CodeMirror.signal(this.cm, "endCompletion", this.cm);
    },

    active: function() {
      return this.cm.state.completionActive === this;
    },

    cursorActivity: function() {
      var pos = this.cm.getCursor();
      var len = this.cm.getLine(pos.line).length;
      if (pos.line != this.startPos.line || len < this.startLen - 1 ||
          pos.ch < this.startPos.ch || this.cm.somethingSelected()) {
        this.close();
      } else {
        var self = this;
        clearTimeout(this.debounce);
        this.debounce = setTimeout(function() { self.update(); }, 70);
      }
    },

    update: function() {
      if (this.tick == null) return;
      var myTick = ++this.tick, self = this;
      var hints = this.getHints(this.cm, this.options);

      if (hints && typeof hints.then === "function") {
        hints.then(function(res) {
          if (self.tick == myTick) self.finishUpdate(res);
        });
      } else {
        this.finishUpdate(hints);
      }
    },

    finishUpdate: function(data) {
      if (this.tick == null) return;
      if (!data || !data.list || !data.list.length) {
        this.close();
        return;
      }
      this.cm.state.completionActive = this;
      if (this.widget) this.widget.close();
      this.widget = new Widget(this, data);
    }
  };

  function Widget(completion, data) {
    this.completion = completion;
    this.data = data;
    this.picked = false;
    var widget = this, cm = completion.cm;

    var hints = this.hints = document.createElement("ul");
    hints.className = "CodeMirror-hints";
    this.selectedHint = 0;

    var completions = data.list;
    for (var i = 0; i < completions.length; ++i) {
      var elt = hints.appendChild(document.createElement("li"));
      var cur = completions[i];
      elt.className = HINT_ELEMENT_CLASS + (i === 0 ? " " + ACTIVE_HINT_ELEMENT_CLASS : "");
      
      if (cur.render) {
        cur.render(elt, data, cur);
      } else {
        elt.appendChild(document.createTextNode(cur.displayText || (typeof cur == "string" ? cur : cur.text)));
      }
      elt.hintId = i;
    }

    var pos = cm.cursorCoords(completion.options.alignWithWord !== false ? data.from : null);
    var left = pos.left, top = pos.bottom, below = true;
    hints.style.left = left + "px";
    hints.style.top = top + "px";

    document.body.appendChild(hints);
    cm.addKeyMap(this.keyMap = buildKeyMap(widget));

    var hintEls = hints.childNodes;
    for (var j = 0; j < hintEls.length; ++j) {
      (function(idx) {
        hintEls[idx].onmousedown = function(e) {
          e.preventDefault();
          widget.changeActive(idx);
          widget.pick();
        };
      })(j);
    }

    // Fermeture automatique en cas de clic en dehors du panneau d'autocomplétion
    this.onOutsideMouseDown = function(e) {
      if (widget.hints && !widget.hints.contains(e.target)) {
        widget.completion.close();
      }
    };
    document.addEventListener("mousedown", this.onOutsideMouseDown, true);

    this.onWindowScrollOrResize = function() {
      if (widget.completion) widget.completion.close();
    };
    window.addEventListener("resize", this.onWindowScrollOrResize);
  }

  Widget.prototype = {
    close: function() {
      if (this.onOutsideMouseDown) {
        document.removeEventListener("mousedown", this.onOutsideMouseDown, true);
        this.onOutsideMouseDown = null;
      }
      if (this.onWindowScrollOrResize) {
        window.removeEventListener("resize", this.onWindowScrollOrResize);
        this.onWindowScrollOrResize = null;
      }
      if (this.hints && this.hints.parentNode) {
        this.hints.parentNode.removeChild(this.hints);
      }
      this.completion.cm.removeKeyMap(this.keyMap);
      this.hints = null;
    },

    changeActive: function(i) {
      if (i >= this.data.list.length) i = this.data.list.length - 1;
      if (i < 0) i = 0;
      if (this.selectedHint == i) return;
      var node = this.hints.childNodes[this.selectedHint];
      if (node) node.className = node.className.replace(" " + ACTIVE_HINT_ELEMENT_CLASS, "");
      node = this.hints.childNodes[this.selectedHint = i];
      if (node) {
        node.className += " " + ACTIVE_HINT_ELEMENT_CLASS;
        if (node.offsetTop < this.hints.scrollTop)
          this.hints.scrollTop = node.offsetTop;
        else if (node.offsetTop + node.offsetHeight > this.hints.scrollTop + this.hints.clientHeight)
          this.hints.scrollTop = node.offsetTop + node.offsetHeight - this.hints.clientHeight;
      }
    },

    pick: function() {
      this.picked = true;
      var completion = this.completion;
      var cur = this.data.list[this.selectedHint];
      var text = typeof cur == "string" ? cur : cur.text;
      
      if (cur.hint) {
        cur.hint(completion.cm, this.data, cur);
      } else {
        completion.cm.replaceRange(text, cur.from || this.data.from, cur.to || this.data.to, "complete");
      }
      completion.close();
    }
  };

  function buildKeyMap(widget) {
    return {
      Up: function() { widget.changeActive(widget.selectedHint - 1); },
      Down: function() { widget.changeActive(widget.selectedHint + 1); },
      PageUp: function() { widget.changeActive(widget.selectedHint - 8); },
      PageDown: function() { widget.changeActive(widget.selectedHint + 8); },
      Home: function() { widget.changeActive(0); },
      End: function() { widget.changeActive(widget.data.list.length - 1); },
      Enter: function() { widget.pick(); },
      Tab: function() { widget.pick(); },
      Esc: function() { 
        widget.completion.close(); 
        return false;
      }
    };
  }

  CodeMirror.defineExtension("showHint", function(options) {
    options = options || {};
    var helper = options.hint || (this.getHelper && this.getHelper(this.getCursor(), "hint"));
    if (!helper && CodeMirror.hint) {
      var modeName = (this.getMode && this.getMode().name) || "python";
      helper = CodeMirror.hint[modeName] || CodeMirror.hint.python || CodeMirror.hint.auto;
    }
    if (helper) return CodeMirror.showHint(this, helper, options);
  });
});

