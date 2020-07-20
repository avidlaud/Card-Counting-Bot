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

<img src="https://user-images.githubusercontent.com/31025257/87994278-860dca80-caba-11ea-9185-859478681525.png" width="450">

Running `detect.py` will begin detection of cards.

## Example

<img src="https://user-images.githubusercontent.com/31025257/87996275-aa1fda80-cabf-11ea-8c85-d2573d58d401.png" width="450">
<img src="https://user-images.githubusercontent.com/31025257/87996412-11d62580-cac0-11ea-9a3e-ff4a31b22782.png" width="150">

The dealer's cards are placed first.  Since the dealer's upcard is a 7, the count is not affected.

<img src="https://user-images.githubusercontent.com/31025257/87996454-3af6b600-cac0-11ea-9823-7631aee31ca8.png" width="450">
<img src="https://user-images.githubusercontent.com/31025257/87996515-7a250700-cac0-11ea-8e20-ca9eace82db1.png" width="150">

The bot's cards are placed.  Both 3 and 5 are "+1" cards and hence the count is updated to 2.  Following basic blackjack strategy, the bot "hits".

<img src="https://user-images.githubusercontent.com/31025257/87996542-95901200-cac0-11ea-96c5-754269ad58c3.png" width="450">
<img src="https://user-images.githubusercontent.com/31025257/87996743-1f3fdf80-cac1-11ea-82a1-37f442e2f7a3.png" width="150">

The bot gets a 2, another "+1" card.  The running total is updated to 3.  Since the bot's hand totals to only 10 and the dealer's upcard is a 7, the bot "hits"

<img src="https://user-images.githubusercontent.com/31025257/87996653-dee06180-cac0-11ea-8931-8dafc922d174.png" width="450">
<img src="https://user-images.githubusercontent.com/31025257/87996778-3d0d4480-cac1-11ea-9ae7-c765dbdc1d57.png" width="150">

The bot is now dealt an 8, which does not have affect the running total.  Now, the bot's hand totals to 18, indicating that it should "Stand".

<img src="https://user-images.githubusercontent.com/31025257/87996834-59a97c80-cac1-11ea-8174-7062df9b96c9.png" width="150">

After the hand is complete and cleared, the bot suggests a bet sizing of 40 (base bet 10) based on its running count of 3.

## Object Detection
YOLOv3 was used for object detection.  Since the original model was implemented in Darknet, [ultralytics's PyTorch port](https://github.com/ultralytics/yolov3) was used instead.

The included weights are trained on a set of Bicycle Standard Index playing cards.  If you wish to train on another set of cards, follow the class order in `data\custom.names`.

## Features and TODO
- [x] Detect card reuse and reset count
- [x] Detect client evaluation framerate and reduce to conserve system resources

- [ ] Multiple deck support
- [ ] Doubling and splitting

