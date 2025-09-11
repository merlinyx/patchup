from PIL import Image
import glob

def make_gif(frames, gif_name):
    # Find the largest width and height
    max_size = max([frame.size for frame in frames], key=lambda x: (x[0], x[1]))

    # Create a list to store resized and centered frames
    resized_frames = []
    
    for frame in frames:
        # Create a transparent canvas with the largest size
        new_frame = Image.new('RGBA', max_size, (255, 255, 255, 0))

        # Get the position to center the image
        offset = ((max_size[0] - frame.size[0]) // 2, (max_size[1] - frame.size[1]) // 2)
        
        # Paste the image onto the canvas
        new_frame.paste(frame, offset)
        
        resized_frames.append(new_frame)

    # Save the first frame and append the rest
    resized_frames[0].save(f"{gif_name}.gif", format="GIF", append_images=resized_frames[1:],
                           save_all=True, duration=200, loop=0) # duration is per frame in ms

def make_gif_from_folder(frame_folder, gif_name):
    frames = [frame for frame in glob.glob(f"{frame_folder}/*.png")]
    frames = sorted(frames, key=lambda x: int(x.split('/')[-1].split('.')[0].split('_')[-1]))
    frames = [Image.open(image) for image in frames]
    make_gif(frames, gif_name)
