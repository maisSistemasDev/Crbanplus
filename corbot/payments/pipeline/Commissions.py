from core.base.pipeline import Pipeline, Step
from payments.models import Commission

class CommissionStepOne(Step):
    def __init__(self):
        self.name:str = "CommissionStepOne"
        self.description:str = "CommissionStepOne"
        self.function = self.validate

    def validate(self, data:dict) -> bool:
        pass
    
    def __str__(self):
        return f"{self.name} - {self.description}"
    
    def __repr__(self): 
        pass