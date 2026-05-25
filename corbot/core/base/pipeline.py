import logging
from typing import Callable, Any, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class Step(ABC):

    name: str
    description: str
    function: Callable
    
    def run(self, *args: Any, **kwargs: Any) -> Any:
        if self.function and callable(self.function):
            return self.function(*args, **kwargs)
        else:
            raise ValueError("Function must be a callable")
    
    def __str__(self):
        return f"{self.name} - {self.description}"
    
    def __repr__(self):
        return f"{self.name} - {self.description}"
    
    def __eq__(self, other):
        return self.name == other.name and self.description == other.description and self.function == other.function


class Pipeline(ABC):
    def __init__(self, steps: List[Step], callback: Callable = None):
        """
        Pipeline class is a class that represents a pipeline.
        """
        self.steps: List[Step] = steps
        self.callback: Callable = callback
    
    def exception_handler(self, step: Step) -> Any:
        try:
            return step.run()
        except Exception as e:
            logger.error(f"Error in step {step.name}: {e}")
            return None
    
    
    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Executa todos os steps da pipeline em sequência.
        
        Args:
            data: Dados de entrada para o primeiro step
            
        Returns:
            Any: Resultado do último step executado
        """
        for step in self.steps:
            data = self.exception_handler(step)
        return data
    
    def add_step(self, step: Step):
        self.steps.append(step)

    def remove_step(self, step: Step):
        self.steps.remove(step)

    def get_steps(self):
        return self.steps

    def __add__(self, other) -> 'Pipeline':
        if isinstance(other, Step):
            self.add_step(other)
        elif isinstance(other, list):
            for step in other:
                self.add_step(step)
        elif isinstance(other, Pipeline):
            self.steps.extend(other.steps)
        return self
    
    def __str__(self):
        return f"Pipeline with {len(self.steps)} steps"
    
    def __repr__(self):
        return f"Pipeline with {len(self.steps)} steps"
    
    def __eq__(self, other: 'Pipeline'):
        return self.steps == other.steps