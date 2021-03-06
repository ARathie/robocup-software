#include "CompositePath.hpp"

using namespace std;
using namespace Geometry2d;

namespace Planning {

CompositePath::CompositePath(unique_ptr<Path> path) { append(std::move(path)); }

void CompositePath::append(unique_ptr<Path> path) {
    if (duration < RJ::Seconds::max()) {
        auto pathDuration = path->getDuration();
        if (pathDuration > RJ::Seconds::zero()) {
            duration += pathDuration;
            paths.push_back(std::move(path));
        } else {
            debugThrow(invalid_argument("The path passed is invalid"));
        }
    } else {
        debugThrow(runtime_error(
            "You can't append to this path. It is already infinitely long."));
    }
}

boost::optional<RobotInstant> CompositePath::evaluate(RJ::Seconds t) const {
    if (t < RJ::Seconds::zero()) {
        debugThrow(
            invalid_argument("A time less than 0 was entered for time t."));
    }

    if (paths.empty()) {
        return boost::none;
    }
    for (const std::unique_ptr<Path>& subpath : paths) {
        RJ::Seconds timeLength = subpath->getDuration();
        t -= timeLength;
        if (t <= RJ::Seconds::zero()) {
            t += timeLength;
            return subpath->evaluate(t);
        }
    }

    return boost::none;
}

bool CompositePath::hit(const Geometry2d::ShapeSet& obstacles,
                        RJ::Seconds startTimeIntoPath,
                        RJ::Seconds* hitTime) const {
    if (paths.empty()) {
        return false;
    }
    int start = 0;
    RJ::Seconds totalTime(0);
    for (const std::unique_ptr<Path>& path : paths) {
        start++;
        RJ::Seconds timeLength = path->getDuration();
        if (timeLength == RJ::Seconds::max()) {
            if (path->hit(obstacles, startTimeIntoPath, hitTime)) {
                if (hitTime) {
                    *hitTime += totalTime;
                }
                return true;
            } else {
                return false;
            }
        }
        startTimeIntoPath -= timeLength;
        if (startTimeIntoPath <= RJ::Seconds::zero()) {
            startTimeIntoPath += timeLength;
            if (path->hit(obstacles, startTimeIntoPath, hitTime)) {
                if (hitTime) {
                    *hitTime += totalTime;
                }
                return true;
            }
            totalTime += timeLength;
            break;
        }
        totalTime += timeLength;
    }

    for (; start < paths.size(); start++) {
        if (paths[start]->hit(obstacles, 0ms, hitTime)) {
            if (hitTime) {
                *hitTime += totalTime;
            }
            return true;
        }
        totalTime += paths[start]->getDuration();
    }
    return false;
}

void CompositePath::draw(SystemState* const state, const QColor& color,
                         const QString& layer) const {
    for (const std::unique_ptr<Path>& path : paths) {
        path->draw(state, color, layer);
    }
}

RJ::Seconds CompositePath::getDuration() const { return duration; }

RobotInstant CompositePath::start() const { return paths.front()->start(); }

RobotInstant CompositePath::end() const { return paths.back()->end(); }

unique_ptr<Path> CompositePath::subPath(RJ::Seconds startTime,
                                        RJ::Seconds endTime) const {
    // Check for valid arguments
    if (startTime < RJ::Seconds::zero()) {
        throw invalid_argument("CompositePath::subPath(): startTime(" +
                               to_string(startTime) +
                               ") can't be less than zero");
    }

    if (endTime < RJ::Seconds::zero()) {
        throw invalid_argument("CompositePath::subPath(): endTime(" +
                               to_string(endTime) +
                               ") can't be less than zero");
    }

    if (startTime > endTime) {
        throw invalid_argument(
            "CompositePath::subPath(): startTime(" + to_string(startTime) +
            ") can't be after endTime(" + to_string(endTime) + ")");
    }

    if (startTime >= duration) {
        debugThrow(invalid_argument("CompositePath::subPath(): startTime(" +
                                    to_string(startTime) +
                                    ") can't be greater than the duration(" +
                                    to_string(duration) + ") of the path"));
        return unique_ptr<Path>(new CompositePath());
    }

    if (startTime == RJ::Seconds::zero() && endTime >= duration) {
        return this->clone();
    }

    // Find the first Path in the vector of paths which will be included in the
    // subPath
    size_t start = 0;
    RJ::Seconds time(0);
    RJ::Seconds lastTime(0);
    while (time <= startTime) {
        lastTime = paths[start]->getDuration();
        time += lastTime;
        start++;
    }

    // Get the time into the Path in the vector of paths which the subPath will
    // start
    RJ::Seconds firstStartTime = (time - lastTime);

    // If the path will only contain that one Path just return a subPath of that
    // Path
    if (time >= endTime) {
        return paths[start - 1]->subPath(startTime - firstStartTime,
                                         endTime - firstStartTime);
    } else {
        // Create a CompositePath initialized with only that first path.
        CompositePath* path = new CompositePath(
            paths[start - 1]->subPath(startTime - firstStartTime));
        unique_ptr<Path> lastPath;
        size_t end;

        // Find the last Path in the vector of paths which will be included in
        // the subPath and store it in lastPath
        if (endTime >= duration) {
            lastPath = paths.back()->clone();
            end = paths.size() - 1;
        } else {
            end = start;
            while (time < endTime) {
                lastTime = paths[start]->getDuration();
                time += lastTime;
                end++;
            }
            end--;
            lastPath = paths[end]->subPath(RJ::Seconds(0),
                                           endTime - (time - lastTime));
        }

        // Add the ones in the middle
        while (start < end) {
            path->append(paths[start]->clone());
            start++;
        }

        // Add the last one
        path->append(std::move(lastPath));

        return unique_ptr<Path>(path);
    }
}

unique_ptr<Path> CompositePath::clone() const {
    CompositePath* newPath = new CompositePath();
    for (const unique_ptr<Path>& path : paths) {
        newPath->append(path->clone());
    }
    return unique_ptr<Path>(newPath);
}

}  // namespace Planning
