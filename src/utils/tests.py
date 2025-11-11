from src.utils.test_set import generate_bordered_test_fabric, generate_palette_colors
from src.utils.bin_pack_api import bin_pack, bin_pack_rail_fence
from src.utils.config import PackingConfig

def print_waste_use(wasted_material, used_material, config=PackingConfig()):
    print(f"Total wasted fabric area: {wasted_material / config.dpi ** 2:.3f} sq in")
    print(f"Total used fabric area: {used_material / config.dpi ** 2:.3f} sq in")
    print(f"Wasted percentage: {wasted_material / used_material * 100:.3f}%")

def total_area(fabrics):
    return sum([f.size[0] * f.size[1] for f in fabrics])

def seam_test1():
    colors = generate_palette_colors(2)
    fabric1 = generate_bordered_test_fabric(colors[0], 200, 200)
    fabric2 = generate_bordered_test_fabric(colors[1], 250, 200)
    packed_fabric, fabrics, wasted, used = bin_pack([fabric1, fabric2])
    print(packed_fabric.size)
    print_waste_use(wasted, used)
    assert packed_fabric.size == (400, 200), 'seam_test1: horizontally composing fabrics with seam allowance should be correct'
    assert len(fabrics) == 0, 'seam_test1: there should be no fabric leftover because exactly two can be used'
    assert used == total_area([fabric1, fabric2]), 'seam_test1: all fabrics are used'
    assert wasted == 0, 'seam_test1: all fabrics should be used up'
    print('seam_test1 passed')

def seam_test2():
    colors = generate_palette_colors(3)
    fabric1 = generate_bordered_test_fabric(colors[0], 140, 200)
    fabric2 = generate_bordered_test_fabric(colors[1], 200, 200)
    fabric3 = generate_bordered_test_fabric(colors[2], 160, 225)
    config = PackingConfig(strategy='courthouse-steps')
    packed_fabric, fabrics, wasted, used = bin_pack([fabric1, fabric2, fabric3], config=config)
    print_waste_use(wasted, used, config=config)
    assert packed_fabric.size == (200, 400), 'seam_test2: vertically composing fabrics with seam allowance should be correct'
    assert len(fabrics) == 0, 'seam_test2: there should be no fabric leftover because exactly three can be used'
    assert used == total_area([fabric1, fabric2, fabric3]), 'seam_test2: all fabrics are used'
    assert abs(wasted - 4e3) < 1e-3, 'seam_test2: the last fabric should create some waste'
    print('seam_test2 passed')

def packing_test1():
    colors = generate_palette_colors(9)
    fabrics = [generate_bordered_test_fabric(color, 150, 150) for color in colors]
    packed_fabric, fabrics, wasted, used = bin_pack(fabrics)
    print_waste_use(wasted, used)
    assert packed_fabric.size == (350, 350), 'packing_test1: log-cabin with 9 squares should have correct packed size'
    assert len(fabrics) == 0, 'packing_test1: there should be no fabric leftover because exactly nine can be used'
    assert used == 150 * 150 * 9, 'packing_test1: all fabrics are used'
    assert wasted == 0, 'packing_test1: all fabrics should be used up'
    print('packing_test1 passed')

def packing_test2():
    colors = generate_palette_colors(9)
    fabrics = [generate_bordered_test_fabric(color, 200, 200) for color in colors]
    config = PackingConfig(strategy='courthouse-steps')
    packed_fabric, fabrics, wasted, used = bin_pack(fabrics, config=config)
    print_waste_use(wasted, used, config=config)
    assert packed_fabric.size == (500, 500), 'packing_test2: courthouse-steps with 9 squares should have correct packed size'
    assert len(fabrics) == 0, 'packing_test2: there should be no fabric leftover because exactly nine can be used'
    assert used == 200 * 200 * 9, 'packing_test2: all fabrics are used'
    assert wasted == 0, 'packing_test2: all fabrics should be used up'
    print('packing_test2 passed')

def packing_test3():
    colors = generate_palette_colors(11)
    fabrics = [generate_bordered_test_fabric(color, 200, 200) for color in colors]
    packed_fabric, fabrics, wasted, used = bin_pack(fabrics, suppress_output=True)
    print_waste_use(wasted, used)
    assert packed_fabric.size == (500, 500), 'packing_test3: log-cabin with additional fabrics not enough for a new strip should have correct packed size'
    assert len(fabrics) == 2, 'packing_test3: there should be two pieces fabric leftover because nine out of eleven should be used'
    assert used == 200 * 200 * 9, 'packing_test3: nine out of eleven fabrics should be used'
    assert wasted == 0, 'packing_test3: all fabrics should be used up or left touched'
    print('packing_test3 passed')

def packing_test4():
    colors = generate_palette_colors(12)
    fabrics = [generate_bordered_test_fabric(color, 350, 150) for color in colors]
    config = PackingConfig(strategy='rail-fence', start_length=350)
    packed_fabric, fabrics, wasted, used = bin_pack_rail_fence(fabrics, config=config)
    print_waste_use(wasted, used, config=config)
    assert packed_fabric.size == (650, 650), 'packing_test4: rail-fence with twelve strips should have correct packed size'
    assert len(fabrics) == 0, 'packing_test4: there should be no fabric leftover because exactly twelve can be used'
    assert used == 350 * 150 * 12, 'packing_test4: all fabrics should be used'
    assert wasted == 0, 'packing_test4: all fabrics should be used up'
    print('packing_test4 passed')

def run_all_tests():
    seam_test1()
    seam_test2()
    packing_test1()
    packing_test2()
    packing_test3()
    packing_test4()

if __name__ == '__main__':
    run_all_tests()
