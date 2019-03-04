# PyTorch tutorial codes for course EL-7143 Advanced Machine Learning, NYU, Spring 2019
# Architecture/model.py: define model
import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from Pipeline.option import args

class ConvNet(nn.Module):
    def __init__(self):
        super(ConvNet, self).__init__()
        nf = 16
        use_batch_norm = not args.no_batch_norm
        # Conv2d(in_channels, out_channels, kernel_size, stride=1, etc.)
        # resized input size = 128
        m_layer = int(math.log2(128) - 2)
        self.net = nn.ModuleList()
        self.net.extend([nn.Conv2d(3, nf, 7, 1, 3)])
        pre_mul, cur_mul = 1, 1
        
        for i in range(m_layer):
            cur_mul = min(2** i, 4)
            _net = []
            if args.use_resnet:
                _net += [ResidualBlock(nf* pre_mul,nf* pre_mul)]
            _net += [nn.Conv2d(nf* pre_mul, nf* cur_mul, 4, 2, 1)]
            if use_batch_norm:
                _net += [nn.BatchNorm2d(nf* cur_mul)]
            _net += [nn.ReLU(True)]
            net = nn.Sequential(*_net)
            self.net.extend([net])
            pre_mul = cur_mul
        self.net.extend([nn.Conv2d(nf* cur_mul, 10, 4, 1, 0)]) # 1     

    def forward(self, x):
        for idx, layer in enumerate(self.net):
            x = layer(x)
        x = x.view(-1, 10)
        return F.log_softmax(x, dim=1)

    def visual_backprop(self, input):
        self.visual_result = []
        self.m_layer = 3
        up_sample = nn.Upsample(scale_factor=2)
        x = input
        for idx, layer in enumerate(self.net):
            x = layer(x)
            _mask = x.mean(dim=1, keepdim = True)
            _max = torch.max(_mask, dim = 2, keepdim = True)[0]
            _max = torch.max(_max, dim=2, keepdim = True)[0]
            mask = _mask / _max.expand_as(_mask)
            self.visual_result += [mask]
            if idx >= self.m_layer:
                break
        final_mask = self.visual_result[self.m_layer]
        for idx in range(self.m_layer-1, -1, -1):
            final_mask = up_sample(final_mask)* self.visual_result[idx]
        res = final_mask.repeat(1,3,1,1) * input
        return res

class ResidualBlock(nn.Module):
    expansion = 1
    def __init__(self, in_planes, planes, stride=1):
        super(ResidualBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, in_planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(in_planes)

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        return out + x

model = ConvNet()
if args.continue_training:
    model.load_state_dict(torch.load('model.pth'))
if args.cuda:
    model.cuda()
    
print('\n---Model Information---')
print('Net:',model)
print('Use GPU:', args.cuda)
