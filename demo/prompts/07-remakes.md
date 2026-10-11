# 07 · Remakes of A4 and A5

The first versions of these two clips had generation errors, found when the user reviewed them:

- **A4 (ATR-01):** the generator added a **second boy in a matching red outfit** in a very wide dome shot with tiny people. CreativAI matched one of the two boys to nearby adults, so the clip was ambiguous.
- **A5 (FC-02):** a person was **sprawled on top of a food counter** in the first second, and a **second child in red** walked past.

## Rules used for the remakes (lessons from the first 14 clips)

1. **Say what is there, not what isn't.** Video models tend to ignore "no X", or even add X because it was mentioned. The prompt describes everyone's clothing colours positively; every exclusion goes in the negative prompt.
2. **Small, calm crowd.** Both broken clips had busy crowds. Fewer background people means fewer merged, duplicated or misplaced bodies.
3. **Simple body actions.** Walking, standing and looking around. No hand-on-face gestures such as rubbing eyes.
4. **Normal lens, medium distance.** No fisheye distortion; people are clearly visible head to toe, not tiny.
5. **One continuous action, no second-by-second script.** Kling didn't follow the timings in the first clips anyway.
6. **Plain menu panels** (pictures of food only), to avoid garbled text and logos.
7. **Camera view matches the map.** Each camera is placed like a real mall camera (3.5–4 m up, ~35° down, so clothing is clearly visible), and the boy enters and leaves on the sides that lead to the previous and next cameras on his path (STR-B → ATR-01 → COR-W → FC-01 → FC-02). The same placement is written in `demo/mall_topology.json`.

Same model and settings as the other clips: Kling O3 image-reference, 16:9, 15 s, std mode, sound off, with the BoyA character sheet as image 1.

## A4 · 14:20 · ATR-01 · The boy alone (remake)

```
Fixed security-camera footage from the north wall of a bright shopping-mall atrium. The camera is mounted about four metres up, directly above the entrance of an electronics store, and looks south across the atrium at a downward angle of about thirty-five degrees. In the middle distance stands a round stone fountain on a cream marble floor with a few benches around it. The wide opening of the main corridor is on the right side of the frame, another corridor opening is on the left, and the mall's glass entrance doors are far in the background. People near the bottom of the frame look large; people at the fountain are medium size, clearly visible head to toe.

The boy is the child shown in image 1 (the image shows the same boy from the front, side and back). He wears a plain bright red t-shirt, blue jeans and white sneakers, exactly as in image 1. He walks out of the store directly below the camera, so he first appears at the bottom of the frame seen from behind. He walks slowly and alone away from the camera toward the fountain, turning his head from side to side as if looking for his parents, then curves to the right and leaves the frame through the corridor opening on the right side.

Around him, a calm afternoon crowd of about eight adults walks at a distance on the marble floor: men in white thobes and women in black abayas, plus a few people in grey, beige or navy clothes. All of them are adults. Everyone walks or stands on the floor.

Locked-off static camera that never moves. Normal wide lens without distortion. Flat, even mall lighting, slightly washed-out colours, light digital noise like real CCTV, everything in focus, real-time speed.
```

## A5 · 14:23 · FC-02 · Lost at the food court (remake)

```
Fixed security-camera footage of a mall food court. The camera is mounted on a wall about three and a half metres up at the edge of the seating area and looks across at a row of fast-food counters along the far wall, at a downward angle of about thirty-five degrees. The counters have plain illuminated menu panels showing pictures of food, and staff in matching dark uniforms stand behind them. A few empty tables are at the bottom of the frame, close to the camera. People in the open space in front of the counters are clearly visible head to toe.

The boy is the child shown in image 1 (the image shows the same boy from the front, side and back). He wears a plain bright red t-shirt, blue jeans and white sneakers, exactly as in image 1. At the start he walks in alone from the bottom right corner of the frame, coming from the seating area, takes a few steps toward the counters and stops in the open space in the middle of the frame. For the rest of the clip he stands there alone, looking around slowly and worriedly, turning his head left and right, with his arms at his sides.

Customers queue calmly in front of the counters and walk past the boy at a distance without stopping, carrying trays: men in white thobes, women in black abayas, and a few people in grey, beige or navy clothes. A few young children hold their parents' hands; they wear white, blue or green. Everyone stands or walks on the floor.

Locked-off static camera that never moves. Normal wide lens without distortion. Flat, even mall lighting, slightly washed-out colours, light digital noise like real CCTV, everything in focus, real-time speed.
```

## Negative prompt for both (replaces the standard one)

```
camera movement, pan, tilt, zoom, handheld shake, cuts, scene change, fisheye, distorted lens, cinematic lighting, shallow depth of field, slow motion, text, subtitles, timestamp, watermark, logo, readable signs, distorted faces, extra limbs, merged people, duplicate person, twins, clones, second child in red, another boy in red, red clothing on anyone else, person lying on a counter, person sitting on a counter, people on furniture, climbing, floating people, morphing clothes, clothes changing colour, flicker, cartoon, CGI look
```
