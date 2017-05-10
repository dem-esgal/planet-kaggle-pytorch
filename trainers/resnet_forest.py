from torch.nn import *
from util import *
from torch import optim
from planet_models.resnet_planet import resnet50_planet, resnet101_planet, resnet152_planet, resnet34_planet
from datasets import *
import torch


is_cuda_availible = torch.cuda.is_available()


def train_resnet_forest(epoch=50):
    criterion = MultiLabelSoftMarginLoss()
    resnet = resnet34_planet()
    logger = Logger('../log/', 'resnet-34')
    optimizer = optim.Adam(lr=1e-4, params=resnet.parameters(), weight_decay=1e-4)
    resnet.cuda()
    resnet = torch.nn.DataParallel(resnet, device_ids=[0, 1])
    train_data_set = train_jpg_loader(256, transform=Compose(
        [
            RandomHorizontalFlip(),
            RandomCrop(224),
            ToTensor()
        ]
    ))
    validation_data_set = validation_jpg_loader(64, transform=Compose(
        [
            Scale(224),
            ToTensor()
         ]
    ))
    best_loss = np.inf
    patience = 0
    for i in range(epoch):
        # evaluating
        val_loss = 0.0
        f2_scores = 0.0
        resnet.eval()
        for batch_index, (val_x, val_y) in enumerate(validation_data_set):
            if is_cuda_availible:
                val_y = val_y.cuda()
            val_y = Variable(val_y, volatile=True)
            val_output = evaluate(resnet, val_x)
            val_loss += criterion(val_output, val_y)
            binary_y = threshold_labels(val_output.data.cpu().numpy())
            f2 = f2_score(val_y.data.cpu().numpy(), binary_y)
            f2_scores += f2
        if best_loss > val_loss:
            best_loss = val_loss
            torch.save(resnet.state_dict(), '../models/resnet-34.pth')
        else:
            print('Reload previous model')
            patience += 1
            resnet.load_state_dict(torch.load('../models/resnet-34.pth'))

        if patience >= 5:
            print('Early stopping!')
            break

        print('Evaluation loss is {}, Training loss is {}'.format(val_loss.data[0]/batch_index, loss.data[0]))
        print('F2 Score is %s' % (f2_scores/batch_index))
        logger.add_record('train_loss', loss.data[0])
        logger.add_record('evaluation_loss', val_loss.data[0]/batch_index)
        logger.add_record('f2_score', f2_scores/batch_index)

        # training
        for batch_index, (target_x, target_y) in enumerate(train_data_set):
            if is_cuda_availible:
                target_x, target_y = target_x.cuda(), target_y.cuda()
            resnet.train()
            target_x, target_y = Variable(target_x), Variable(target_y)
            optimizer.zero_grad()
            output = resnet(target_x)
            loss = criterion(output, target_y)
            loss.backward()
            optimizer.step()

        print('Finished epoch {}'.format(i))
    logger.save()
    logger.save_plot()


if __name__ == '__main__':
    train_resnet_forest(epoch=85)

