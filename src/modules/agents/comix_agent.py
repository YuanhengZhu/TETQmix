import torch as th
import torch.nn as nn

from ..layer.transformer import Transformer


class CEMRecurrentAgent(nn.Module):
    def __init__(self, input_shape, args):
        super(CEMRecurrentAgent, self).__init__()
        self.args = args
        self.n_agents = args.n_agents
        self.n_entities = args.n_entities
        self.feat_dim = args.obs_entity_feats - 1  # !!!!!!
        self.task_dim = args.task_feats
        self.emb_dim = args.emb

        # embedder
        self.feat_embedding = nn.Linear(self.feat_dim, self.emb_dim)

        # transformer block
        self.transformer = Transformer(
            args.emb, args.heads, args.depth, args.ff_hidden_mult, args.dropout
        )

        # important!
        self.q_basic = nn.Linear(args.emb + args.n_actions, 1)

    def init_hidden(self):
        # make hidden states on same device as model
        return th.zeros(1, self.args.emb).to(self.args.device)

    def forward(self, inputs, hidden_state, actions):
        # prepare the inputs
        ba, _ = inputs.size()  # batch_size*agents, features
        inputs = inputs[:, :-self.task_dim]
        inputs = inputs.view(-1, self.n_entities, self.feat_dim + 1)
        hidden_state = hidden_state.view(-1, 1, self.emb_dim)

        mask = inputs[:, :, -1:]
        inputs = inputs[:, :, :-1]

        embs = self.feat_embedding(inputs)

        x = th.cat((hidden_state, embs), 1)
        mask = th.cat((th.ones_like(hidden_state[:, :, 0:1]), mask), 1)

        embs = self.transformer.forward(x, x, mask)

        h = embs[:, 0:1, :]

        # get the q values
        z = th.cat((h, actions.contiguous().view(-1, 1, actions.shape[-1])), dim=-1)
        q = self.q_basic(z)
        
        # q = q.view(b, a, -1)
        # h = h.view(b, a, -1)
        return {"Q": q, "hidden_state": h}
