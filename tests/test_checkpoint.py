import torch

from training import checkpoint
from training.backends import make_backend
from training.model import GPT
from training.optim import make_optimizer

CTX = 22


def test_save_load_bitwise(tmp_path):
    torch.manual_seed(1)
    m1 = GPT(392, d=64, nl=2, nh=4, ctx=CTX)
    o1 = make_optimizer(m1, 3e-3, 0.1)
    # take one real step so optimizer moments are non-trivial
    loss = m1(torch.randint(0, 392, (4, CTX)))[0].float().pow(2).mean()
    loss.backward()
    o1.step()
    p = str(tmp_path / "ck.pt")
    checkpoint.save(p, m1, o1, step=1, base_lr=3e-3, warmup=100,
                    manifest_hash="x", backend=make_backend("cpu"))

    torch.manual_seed(2)                       # different init on purpose
    m2 = GPT(392, d=64, nl=2, nh=4, ctx=CTX)
    o2 = make_optimizer(m2, 3e-3, 0.1)
    step = checkpoint.load(p, m2, o2, 3e-3, 100)
    assert step == 1
    for k, t in m1.state_dict().items():
        assert t.numpy().tobytes() == m2.state_dict()[k].numpy().tobytes(), k
    s1, s2 = o1.state_dict()["state"], o2.state_dict()["state"]
    assert s1.keys() == s2.keys()
    for k in s1:
        for f in ("exp_avg", "exp_avg_sq"):
            assert s1[k][f].numpy().tobytes() == s2[k][f].numpy().tobytes()
