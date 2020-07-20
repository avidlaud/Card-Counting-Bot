# Card-Counting-Bot
A (cheating) bot to play blackjack against.

Utilizes a Python PyTorch implementation of the YOLOv3 model for object detection.  Trained on a custom dataset of playing cards (augmented by my [synthetic image generator](https://github.com/avidlaud/Synthetic-Image-Generator)).

Plays using the single-deck "Hi-Lo" card counting strategy and basic blackjack strategy.

## Prerequisites
A list of dependencies are stored in `requirements.txt`

```
pip install -r requirements.txt
```

## Usage
A webcam should be used as the input data stream.  The perspective should be positioned as if the bot were a player at a table.  The bot's cards should be placed "near" it - in the bottom half of the webcam's field of view. The dealer's cards should be "far" - in the top half of the webcam's field of view.

Running `detect.py` will begin detection of cards.

## Object Detection
YOLOv3 was used for object detection.  Since the original model was implemented in Darknet, [ultralytics's PyTorch port](https://github.com/ultralytics/yolov3) was used instead.

The included weights are trained on a set of Bicycle Standard Index playing cards.  If you wish to train on another set of cards, follow the class order in `data\custom.names`.
