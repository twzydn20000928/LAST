"""Late predicted-clean guidance for each paper-specified scheduler family."""
from diffusers import FlowMatchEulerDiscreteScheduler,UniPCMultistepScheduler
from .lfg import perturbation

class LFGFlowEuler(FlowMatchEulerDiscreteScheduler):
    spread=None
    alpha=.15
    late_steps=10
    def step(self,model_output,timestep,sample,*args,**kwargs):
        if self.step_index is None:self._init_step_index(timestep)
        if self.spread is not None and self.step_index>=len(self.timesteps)-self.late_steps:
            sigma=self.sigmas[self.step_index].to(sample.device)
            if float(sigma)<=0:raise ValueError('Cannot guide zero-sigma Euler step')
            clean=sample.float()-sigma*model_output.float()
            delta=getattr(self,'carrier_perturbation',perturbation)(clean,self.spread,self.alpha)
            model_output=model_output.float()-delta/sigma
        return super().step(model_output,timestep,sample,*args,**kwargs)

class LFGUniPC(UniPCMultistepScheduler):
    spread=None
    alpha=.15
    late_steps=10
    def convert_model_output(self,model_output,*args,**kwargs):
        clean=super().convert_model_output(model_output,*args,**kwargs)
        if self.spread is not None and self.step_index>=len(self.timesteps)-self.late_steps:
            if not self.predict_x0 or self.config.prediction_type!='flow_prediction':raise ValueError('LFG requires flow predicted-clean UniPC')
            clean=clean+getattr(self,'carrier_perturbation',perturbation)(clean,self.spread,self.alpha)
        return clean
