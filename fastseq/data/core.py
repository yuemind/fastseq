# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_data.core.ipynb (unless otherwise specified).

__all__ = ['NormalizeSeq', 'NormalizeSeqMulti', 'make_test', 'split_file', 'multithread_f', 'TSSplitter',
           'MTSDataLoaders']

# Cell
from .load import *
from ..core import *
from fastcore.all import *
from fastcore.imports import *
from fastai2.basics import *
from fastai2.data.transforms import *
from fastai2.tabular.core import *
from .load import *
import orjson

# Cell
def _zeros_2_ones(o, eps=1e-8):
    nan_mask = o!=o
    o[o < eps ] = 1
    o[nan_mask ] = 1
    return o


# Cell
class NormalizeSeq(Transform):
    def __init__(self, verbose=False, make_ones=True, eps=1e-7, mean = None):
        store_attr(self,'verbose, make_ones, eps, mean')
        self.m, self.s = 0, 1

    def to_same_device(self, o):
        if o.is_cuda:
            self.m, self.s = to_device(self.m,'cuda'), to_device(self.s,'cuda')
        else:
            self.m, self.s = to_cpu(self.m), to_cpu(self.s)

    def encodes(self, o: TensorSeq):
        self.m = torch.mean(o, -1, keepdim=True)
        self.s = torch.std(o,  -1, keepdim=True) +self.eps
        if (self.s < self.eps*10).sum():
            self.s = _zeros_2_ones(self.s, self.eps*10)
        if self.verbose:
            print('encodes',[a.shape for a in o],
                  'm shape', {k:o.shape for k,o in self.m.items()},
                  's shape',{k:o.shape for k,o in self.s.items()})

        return self.norm(o)

    def norm(self, o):
        return (o - self.m)/self.s

    def decodes(self, o: TensorSeq):
        if self.verbose:
            print('decodes',o.shape,
                  'm shape',self.m.shape,
                  's shape',self.s.shape)
        return self.denorm(o)

    def denorm(self, o):
        self.to_same_device(o)
        return (o*self.s)+self.m

# Cell
class NormalizeSeqMulti(ItemTransform):
    """A shell Transformer to normalize `TensorSeqs` inside `TSMulti_` with `NormalizeSeqs`. """
    @delegates(NormalizeSeq.__init__)
    def __init__(self, n_its=5, **kwargs):
        """`n_its` does not include the ts to predict."""
        self.f = {i:NormalizeSeq(**kwargs) for i in range(n_its)}
        self.n = n_its

    def encodes(self, o:TSMulti_):
        r = L()
        for i,a in enumerate(o):
            if type(a) is not TensorSeq:
                r.append(a)
            elif i < (self.n-1):
                r.append(self.f[i](a))
            else:
                r.append(self.f[0].norm(o[i]))
        return TSMulti_(r)

    def decodes(self, o:TSMulti_):
        r = L(self.f[i].decode(a) for i,a in enumerate(o[:-1]))
        r.append(self.f[0].denorm(o[-1]))
        return TSMulti_(r)


# Cell
def make_test(ts:dict, horizon:int, lookback:int, keep_lookback:bool = False):
    """Splits the every ts in `items` based on `horizon + lookback`*, where the last part will go into `val` and the first in `train`.
    *if `keep_lookback`:
        it will only remove `horizon` from `train` otherwise will also remove lookback from `train`.
    """
    train,val = {},{}
    for k,v in ts.items():
        if k in ['ts_con','ts_cat']:
            if keep_lookback:
                train[k] = [o[:-(horizon)] for o in v]
            else:
                train[k] = [o[:-(horizon+lookback)] for o in v]
            val[k] = [o[-(horizon+lookback):] for o in v]
        elif k == '_length':
            train[k] = v - (horizon if keep_lookback else horizon+lookback)
            val[k] = horizon+lookback
        else:
            train[k] = v
            val[k] = v
    return train, val

# Cell
@delegates(make_test)
def split_file(file, folder='valid', **kwargs):
    ts = get_ts_datapoint(file)
    t, v = make_test(ts, **kwargs)
    open(file,'wb').write(orjson.dumps(t))

    # in the new folder
    new_f = Path(*str(file).split(os.sep)[:-1]) / folder / str(file).split(os.sep)[-1]
    if not new_f.parent.exists(): new_f.parent.mkdir()
    open(new_f,'wb').write(orjson.dumps(v))
    return file, new_f

# Cell
def multithread_f(f,o:list, num_workers = None):
    from multiprocessing.dummy import Pool as ThreadPool
    pool = ThreadPool(num_workers)
    r = pool.map(f, o)
    return r


# Cell
@delegates(split_file)
def TSSplitter(**kwargs):
    "Create function that splits `items` between train/val."
    def _inner(o):
        return split_file(o, **kwargs)
    return _inner

# Cell
class MTSDataLoaders(DataLoaders):
    @classmethod
    @delegates(MTSDataLoader.__init__)
    def from_path(cls, path, y_name:str, horizon:int, lookback=None, step=1,
                   device=None, norm=True, valid_pct=1.5, splitter = None, **kwargs):
        """Create `MTSDataLoaders` from a path.

        Defaults to splitting the data if no folder `valid` exists in `path`.
        """
        lookback = ifnone(lookback, horizon * 3)
        device = ifnone(device, default_device())
        train, valid = get_train_valid_ts(path, horizon, lookback, valid_pct)
        if norm and 'after_batch' not in kwargs:
            kwargs.update({'after_batch':L(NormalizeSeqMulti(n_its=5))})
        db = DataLoaders(*[MTSDataLoader(ds, y_name, horizon=horizon, lookback=lookback, step=step,
                                        device=device, **kwargs)
                           for ds in [train,valid]], path=path, device=device)
        print(f"Train:{db.train.n}; Valid: {db.valid.n}")
        return db