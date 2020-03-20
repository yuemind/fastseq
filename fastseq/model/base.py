# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/10_model.base.ipynb (unless otherwise specified).

__all__ = ['SeqTab', 'M5Learner', 'SeqTabLearner', 'make_pred', 'make_submision_file', 'dct']

# Cell
from ..core import *
from ..data.load import *
from ..data.core import *
from ..data.procs import *
from fastcore.all import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.data.transforms import *
from fastai2.tabular.core import *
from fastai2.torch_basics import *
from fastai2.callback.all import *
from ..metrics import *

# Cell
class SeqTab(Module):
    """Basic model for sequential data."""
    def __init__(self, n_cont, out_sz, layers, y_range=None,):
        ps = [0]*len(layers)
        sizes = [n_cont] + layers + [out_sz]
        actns = [nn.ReLU(inplace=True) for _ in range(len(sizes)-2)] + [None]
        _layers = [LinBnDrop(sizes[i], sizes[i+1], bn=True and (i!=len(actns)-1), p=p, act=a)
                       for i,(p,a) in enumerate(zip(ps+[0.],actns))]
        if y_range is not None: _layers.append(SigmoidRange(*y_range))
        self.bn_cont = nn.BatchNorm1d(n_cont)
        if y_range is not None: _layers.append(SigmoidRange(*y_range))
        self.layers = nn.Sequential(*_layers)

    def forward(self, x, ts_con, ts_cat, cat, con):
        x_bn = self.bn_cont(x[:,0])
        o = [x, self.layers(x_bn)[:,None,:]]
        return torch.cat(o,-1)

# Cell
class M5Learner(Learner): pass

@delegates(M5Learner.__init__)
def SeqTabLearner(dls, layers=None,metrics=None, **kwargs):
    "Get a `Learner` using `data`, with `metrics`, including a `SeqTab` created using the remaining params."
    if layers is None: layers = [200,100]
    model = SeqTab(dls.train.lookback, dls.train.horizon, layers,)
    return Learner(dls, model, loss_func = F.mse_loss, opt_func= ranger, metrics=L(metrics)+L(mae, smape,mae), **kwargs)

# Cell
# inputs,preds,targs,decoded,losses
def make_pred(learn, dl = 2):
    inputs,preds,targs,decoded,losses = learn.get_preds(3, with_decoded = True, with_input=True, with_loss=True)
    predictions = (decoded - targs[:,0,-28:].mean(-1)[:,None,None]).round() #TODO std
    return predictions[:,0,:]


# Cell
def make_submision_file(learn):
    dct = {}
    for i, (file, pred) in enumerate(zip(learn.dls[2].dataset, make_pred(learn, 2))):
        name = file.name.replace('.json','_validation')
        pred =','.join(L(list(pred[-28:].numpy())).map(int).map(str))
        dct[name] = pred

    for i, (file, pred) in enumerate(zip(learn.dls[3].dataset, make_pred(learn, 3))):
        name = file.name.replace('.json','_evaluation')
        pred =','.join(L(list(pred[-28:].numpy())).map(int).map(str))
        dct[name] = pred
    return dct

# Cell
dct = make_submision_file(learn)
dct['HOBBIES_1_028_CA_1_validation']

# Cell
make_file(learn, dct)