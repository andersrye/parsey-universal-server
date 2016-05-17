#!/usr/bin/python3

# sudo apt-get install python3-pip
# sudo pip3 install flask

import subprocess

from flask import Flask, request, make_response, jsonify

app = Flask(__name__)

ROOT_DIR = "models/syntaxnet"
PARSER_EVAL = "bazel-bin/syntaxnet/parser_eval"
MODEL_DIR = "syntaxnet/models/parsey_mcparseface"

@app.route('/')
def index():
  q = request.args.get("q", "")

  # Run the part-of-speech tagger model.
  result_postag = subprocess.check_output([
    PARSER_EVAL,
    "--input=stdin",
    "--output=stdout-conll",
    "--hidden_layer_sizes=64",
    "--arg_prefix=brain_tagger",
    "--graph_builder=structured",
    "--task_context=" + MODEL_DIR + "/context.pbtxt",
    "--model_path=" + MODEL_DIR + "/tagger-params",
    "--slim_model",
    "--batch_size=1024",
    "--alsologtostderr",
  ],
    input=q.encode("utf8"),
    cwd=ROOT_DIR,
  )

  # Run the syntactic dependency model.
  result_syntax = subprocess.check_output([
    PARSER_EVAL,
    "--input=stdin-conll",
    "--output=stdout-conll",
    "--hidden_layer_sizes=512,512",
    "--arg_prefix=brain_parser",
    "--graph_builder=structured",
    "--task_context=" + MODEL_DIR + "/context.pbtxt",
    "--model_path=" + MODEL_DIR + "/parser-params",
    "--slim_model",
    "--batch_size=1024",
    "--alsologtostderr",
  ],
    input=result_postag,
    cwd=ROOT_DIR,
  )

  # Generate a nice ASCII tree.
  tree = subprocess.check_output([
    "bazel-bin/syntaxnet/conll2tree",
    "--task_context=" + MODEL_DIR + "/context.pbtxt",
    "--alsologtostderr"
  ],
    input=result_syntax,
    cwd=ROOT_DIR,
  )

  # Format the result.
  def format_token(line):
    x = dict(zip(
     ["id", "token", "unknown1", "pos1", "pos2", "unknown2", "parent", "relation", "unknown3", "unknown4"],
     line.split("\t")
    ))
    x["id"] = int(x["id"])
    x["parent"] = int(x["parent"])
    del x["unknown1"]
    del x["unknown2"]
    del x["unknown3"]
    del x["unknown4"]
    return x
                                   
  result = [
    format_token(line)
    for line in result_syntax.decode("utf8").split("\n")
    if line.strip() != ""
  ]

  return jsonify(
    q=q,
    tree=tree.decode("utf8").strip().split("\n")[2:], # first two lines are meta
    result=result
  )

if __name__ == '__main__':
    app.run(debug=True, port=80, host="0.0.0.0")

