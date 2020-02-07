# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/07_nbeats.learner.ipynb (unless otherwise specified).

__all__ = ['nbeats_learner']

# Cell
from fastcore.utils import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.callback.hook import num_features_model
from fastai2.callback.all import *
from fastai2.torch_core import *
from torch.autograd import Variable
from ..all import *

from .model import *
from .callbacks import *

# Cell
# from fastai2.basics import *
# from fastseq.all import *

@delegates(NBeatsNet.__init__)
def nbeats_learner(dbunch:TSDataLoaders, output_channels=None, metrics=None,cbs=None, b_loss=0., loss_func=None, opt_func=None, **kwargs):
    "Build a N-Beats style learner"
    model = NBeatsNet(
        device = dbunch.train.device,
        horizon = dbunch.train.horizon,
        lookback = dbunch.train.lookback,
        **kwargs
       )

    loss_func = ifnone(loss_func, CombinedLoss(F.mse_loss, dbunch.train.lookback))
    cbs = L(cbs)
    if b_loss != 0.:
        raise NotImplementedError()
        cbs.append(NBeatsBLoss(b_loss))
    opt_func = ifnone(opt_func, ranger)
    learn = Learner(dbunch, model, loss_func=loss_func, opt_func= opt_func,
                    metrics=L(metrics)+L(mae, smape, NBeatsTheta(),
                                         NBeatsBackwards(dbunch.train.lookback), NBeatsForward(dbunch.train.lookback)
                                        ),
                    cbs=L(NBeatsAttention())+cbs
                   )
    learn.lh = (dbunch.train.lookback/dbunch.train.horizon)
    return learn