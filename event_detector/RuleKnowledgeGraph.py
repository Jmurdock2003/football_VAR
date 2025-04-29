# RuleKnowledgeGraph.py
class RuleKnowledgeGraph:
    def __init__(self):
        self.graph = {
            "Offside Rule": {
                "Check Moment": "Ball is kicked",
                "Condition": "Attacker must not be closer to goal line than second-last defender and ball"
            },
            "Throw-In Rule": {
                "Check Moment": "Ball crosses side touchline",
                "Condition": "Ball entirely leaves field on sides"
            },
            "Goal Kick Rule": {
                "Check Moment": "Ball crosses goal line",
                "Condition": "Last touched by attacking team = goal kick"
            },
            "Corner Rule": {
                "Check Moment": "Ball crosses goal line",
                "Condition": "Last touched by defending team = corner kick"
            }
        }

    def get_rule(self, rule_name):
        return self.graph.get(rule_name, None)
