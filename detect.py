import argparse

from models import *  # set ONNX_EXPORT in models.py
from utils.datasets import *
from utils.utils import *
from utils.blackjack_utils import *
import numpy as np

running_total = 0
seen_cards = [False] * 52

#Stucture: [[my_cards], [dealer_cards]]
past_five = []
past_four = []
past_three = []
past_two = []
past_one = []

prev_seen = []

current_cards = []

confirmed_my_hand = []
confirmed_dealer_hand = []

card_values = load_card_values('data/card.values')

def detect(save_img=False):
    imgsz = (320, 192) if ONNX_EXPORT else opt.img_size  # (320, 192) or (416, 256) or (608, 352) for (height, width)
    out, source, weights, half, view_img, save_txt = opt.output, opt.source, opt.weights, opt.half, opt.view_img, opt.save_txt
    webcam = source == '0' or source.startswith('rtsp') or source.startswith('http') or source.endswith('.txt')

    # Initialize
    device = torch_utils.select_device(device='cpu' if ONNX_EXPORT else opt.device)
    if os.path.exists(out):
        shutil.rmtree(out)  # delete output folder
    os.makedirs(out)  # make new output folder

    # Initialize model
    model = Darknet(opt.cfg, imgsz)

    # Load weights
    attempt_download(weights)
    if weights.endswith('.pt'):  # pytorch format
        model.load_state_dict(torch.load(weights, map_location=device)['model'])
    else:  # darknet format
        load_darknet_weights(model, weights)

    # Second-stage classifier
    classify = False
    if classify:
        modelc = torch_utils.load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model'])  # load weights
        modelc.to(device).eval()

    # Eval mode
    model.to(device).eval()

    # Fuse Conv2d + BatchNorm2d layers
    # model.fuse()

    # Export mode
    if ONNX_EXPORT:
        model.fuse()
        img = torch.zeros((1, 3) + imgsz)  # (1, 3, 320, 192)
        f = opt.weights.replace(opt.weights.split('.')[-1], 'onnx')  # *.onnx filename
        torch.onnx.export(model, img, f, verbose=False, opset_version=11,
                          input_names=['images'], output_names=['classes', 'boxes'])

        # Validate exported model
        import onnx
        model = onnx.load(f)  # Load the ONNX model
        onnx.checker.check_model(model)  # Check that the IR is well formed
        print(onnx.helper.printable_graph(model.graph))  # Print a human readable representation of the graph
        return

    # Half precision
    half = half and device.type != 'cpu'  # half precision only supported on CUDA
    if half:
        model.half()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = True
        torch.backends.cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz)
    else:
        save_img = True
        dataset = LoadImages(source, img_size=imgsz)

    # Get names and colors
    names = load_classes(opt.names)
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(names))]

    # Run inference
    t0 = time.time()
    img = torch.zeros((1, 3, imgsz, imgsz), device=device)  # init img
    _ = model(img.half() if half else img.float()) if device.type != 'cpu' else None  # run once

    frame_number = 0
    frame_timings = []
    frame_skip = 1

    for path, img, im0s, vid_cap in dataset:
        if frame_number % frame_skip == 0:
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()  # uint8 to fp16/32
            img /= 255.0  # 0 - 255 to 0.0 - 1.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)

            # Inference
            t1 = torch_utils.time_synchronized()
            pred = model(img, augment=opt.augment)[0]
            t2 = torch_utils.time_synchronized()

            #Use 10 frames to calculate timing for frames
            if 10 < frame_number < 21:
                frame_timings.append(t2-t1)
            if frame_number == 21:
                frame_skip = adjust_for_fps(frame_timings)
                print(frame_skip)

            # to float
            if half:
                pred = pred.float()

            # Apply NMS
            pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres,
                                    multi_label=False, classes=opt.classes, agnostic=opt.agnostic_nms)

            # Apply Classifier
            if classify:
                pred = apply_classifier(pred, modelc, img, im0s)

            #Blackjack full frame parameters:
            cards_in_frame = []

            # Process detections
            for i, det in enumerate(pred):  # detections for image i
                #Blackjack parameters:
                card_x, card_y, card_class = 0, 0, 0
                if webcam:  # batch_size >= 1
                    p, s, im0 = path[i], '%g: ' % i, im0s[i].copy()
                else:
                    p, s, im0 = path, '', im0s
                s += '%gx%g ' % img.shape[2:]  # print string
                gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  #  normalization gain whwh
                if det is not None and len(det):
                    # Rescale boxes from imgsz to im0 size
                    det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                    # Print results
                    for c in det[:, -1].unique():
                        n = (det[:, -1] == c).sum()  # detections per class
                        s += '%g %ss, ' % (n, names[int(c)])  # add to string

                    # Write results
                    for *xyxy, conf, cls in det:
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        #Blackjack information
                        # print(xywh[:2])
                        card_class, card_x, card_y = int(cls), xywh[0], xywh[1]
                        cards_in_frame.append((card_class, card_x, card_y))

                        if save_img or view_img:  # Add bbox to image
                            label = '%s %.2f' % (names[int(cls)], conf)
                            plot_one_box(xyxy, im0, label=label, color=colors[int(cls)])

                # Print time (inference + NMS)
                # print('%sDone. (%.3fs)' % (s, t2 - t1))

                # Stream results
                if view_img:
                    cv2.imshow(p, im0)
                    if cv2.waitKey(1) == ord('q'):  # q to quit
                        raise StopIteration
            
            #Blackjack gameplay
            evaluate_position(cards_in_frame, names)

        frame_number += 1

    print('Done. (%.3fs)' % (time.time() - t0))

def update_seen_cards():
    global seen_cards
    global running_total
    #If seen in at least three out of five past frames, card is valid:
    all_seen = []
    past_lists = [past_five, past_four, past_three, past_two, past_one]
    for l in past_lists:
        for sublist in l:
            all_seen += sublist
    confirmed_cards = []
    for num in set(all_seen):
        if all_seen.count(num) >= 3:
            confirmed_cards.append(num)
    #Determine if there is a new card
    # print(all_seen)
    # print(confirmed_cards)
    # new_cards = set(all_seen).difference(set(confirmed_cards))
    # new_cards = np.setdiff1d(confirmed_cards, all_seen)
    far_past = past_four + past_five
    far_p = []
    for subl in far_past:
        for item in subl:
            far_p.append(item)
    new_cards = set(confirmed_cards).difference(set(far_p))
    for new_card in new_cards:
        if seen_cards[new_card]:
            #Card has already been seen - new deck, restart count
            running_total = 0
            # print("****************************RESET CARD COUNT****************************")
            seen_cards = [False] * 52
        else:
            seen_cards[new_card] = True
            #Update card count
            card_val = int(card_values[new_card])
            # print("*********************************CARD_VALUE*********************************", card_val, new_card)
            if 2 <= card_val <= 6:
                running_total += 1
            elif 7 <= card_val <= 9:
                #No change
                continue
            else:
                running_total -= 1
    


def evaluate_position(cards, names):
    global past_five
    global past_four
    global past_three
    global past_two
    global past_one
    my_cards = []
    dealer_cards = []
    update_seen_cards()
    for card in cards:
        card_class, card_x, card_y = card
        if card_y > 0.5:
            my_cards.append(card_class)
        else:
            dealer_cards.append(card_class)

    hand_value = 0
    my_card_names = [names[x] for x in my_cards]
    dealer_card_names = [names[y] for y in dealer_cards]
    print("MY CARDS:", my_card_names)
    print("DEALER CARDS:", dealer_card_names)
    my_card_values = [int(card_values[x]) for x in my_cards]
    dealer_card_values = [int(card_values[y]) for y in dealer_cards]
    # print("EVALUATED:", cards)
    # print("MY CARDS:", my_cards)
    # print("MY HAND VALUE")
    # print(evaluate_hand(my_card_values))
    # print("DEALER CARDS:", dealer_cards)
    # print("DEALER HAND VALUE")
    # print(evaluate_hand(dealer_card_values))
    if len(my_cards) > 0 and len(dealer_cards) > 0:
        if strategy(my_card_values, dealer_card_values):
            print("**********HIT**********")
        else:
            print("**********STAND**********")
    if len(my_cards) == 0 and len(dealer_cards) == 0:
        if running_total >= 0:
            bet_size = 10*(running_total+1)
        else:
            bet_size = 10
        print("BET:", bet_size)
    print("RUNNING TOTAL:", str(running_total))
    past_five = past_four.copy()
    past_four = past_three.copy()
    past_three = past_two.copy()
    past_two = past_one.copy()
    # past_one = [my_card_values.copy(), dealer_card_values.copy()]
    past_one = [my_cards.copy(), dealer_cards.copy()]


def evaluate_hand(hand):
    '''
    Accepts a list of card values to evaluate the hand.
    Aces represented as "1"
    '''
    cards = hand
    values = [0]
    for card in cards:
        extra_vals = []
        for i in range(len(values)):
            values[i] += card
            if card == 1:
                extra_vals.append(values[i] + 10)
        values += extra_vals
    return [x for x in values if x <= 21]

def strategy(my_hand, dealer_hand):
    #Has ace in hand - soft total
    my_hand_eval = evaluate_hand(my_hand)
    if len(my_hand_eval) == 0:
        #Bust
        return False
    else:
        my_hand_value = sorted(my_hand_eval)[-1]
    print(my_hand_value)
    #Dealer only has one up facing card
    dealer_card = dealer_hand[0]
    #Soft value
    if 1 in my_hand and len(my_hand) == 2:
        if 12 <= my_hand_value <= 17:
            return True
        elif my_hand_value == 18:
            return True if 9 <= dealer_card <= 10 else False
        else:
            return False
    #Hard value
    else:
        if 5 <= my_hand_value <= 11:
            return True
        elif my_hand_value == 12:
            return False if 4 <= dealer_card <= 6 else True
        elif 13 <= my_hand_value <= 16:
            return False if 2 <= dealer_card <= 6 else True
        else:
            return False



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, default='cfg/yolov3-spp.cfg', help='*.cfg path')
    parser.add_argument('--names', type=str, default='data/custom.names', help='*.names path')
    parser.add_argument('--weights', type=str, default='weights/last.pt', help='weights path')
    parser.add_argument('--source', type=str, default='0', help='source')  # input file/folder, 0 for webcam
    parser.add_argument('--output', type=str, default='output', help='output folder')  # output folder
    parser.add_argument('--img-size', type=int, default=512, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.3, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.6, help='IOU threshold for NMS')
    parser.add_argument('--fourcc', type=str, default='mp4v', help='output video codec (verify ffmpeg support)')
    parser.add_argument('--half', action='store_true', help='half precision FP16 inference')
    parser.add_argument('--device', default='', help='device id (i.e. 0 or 0,1) or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    opt = parser.parse_args()
    opt.cfg = check_file(opt.cfg)  # check file
    opt.names = check_file(opt.names)  # check file
    print(opt)

    with torch.no_grad():
        detect()
